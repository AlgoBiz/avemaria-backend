import os
import json
import logging
import uuid
import stripe
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from apps.students.models import Student
from apps.courses.models import Course, CourseEnrollment
from apps.resources.models import PaidResource, ResourcePurchase
from apps.payments.models import PaymentTransaction
from apps.resources.emails import send_purchase_receipt_email
from apps.courses.emails import send_course_enrollment_receipt_email

from .serializers import (
    PaymentConfigSerializer,
    CreateCheckoutSessionSerializer,
    CheckoutSessionResponseSerializer,
    VerifySessionSerializer,
    VerifySessionResponseSerializer,
    StripeWebhookPayloadSerializer,
    PaymentTransactionSerializer,
    PaymentTransactionDetailSerializer,
)

logger = logging.getLogger(__name__)


def get_stripe_currency(currency_symbol_or_code):
    """Maps currency symbols like £, $, € to ISO 4217 lowercase codes."""
    if not currency_symbol_or_code:
        return getattr(settings, 'STRIPE_CURRENCY', 'gbp').lower()
    mapping = {
        '£': 'gbp',
        '$': 'usd',
        '€': 'eur',
        '₹': 'inr',
    }
    clean = str(currency_symbol_or_code).strip().lower()
    return mapping.get(clean, clean if len(clean) == 3 else getattr(settings, 'STRIPE_CURRENCY', 'gbp').lower())


def stripe_to_dict(obj):
    """
    Safely converts a StripeObject or dict to a standard Python dict.
    In stripe-python v8+, StripeObject does not have dict methods like .get().
    """
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, 'to_dict'):
        try:
            return obj.to_dict()
        except Exception:
            pass
    if hasattr(obj, '__getitem__'):
        try:
            return {k: obj[k] for k in obj}
        except Exception:
            pass
    return {}


def fulfill_checkout_session(session, request=None):
    """
    Idempotent fulfillment helper for a successful Stripe Checkout Session.
    Activates the CourseEnrollment or ResourcePurchase, updates the PaymentTransaction,
    and sends branded tax invoice receipts to the student.
    """
    session_dict = stripe_to_dict(session)
    session_id = session_dict.get('id') or getattr(session, 'id', None)
    metadata = stripe_to_dict(session_dict.get('metadata')) or stripe_to_dict(getattr(session, 'metadata', None))
    payment_intent = session_dict.get('payment_intent') or getattr(session, 'payment_intent', '')

    item_type = metadata.get('item_type')
    item_id = metadata.get('item_id')
    student_id = metadata.get('student_id')
    tx_id = metadata.get('transaction_id')

    # Find transaction
    transaction = None
    if tx_id:
        transaction = PaymentTransaction.objects.filter(id=tx_id).first()
    if not transaction and session_id:
        transaction = PaymentTransaction.objects.filter(stripe_session_id=session_id).first()

    student = None
    if student_id:
        student = Student.objects.filter(id=student_id).first()
    elif transaction:
        student = transaction.student

    if not student or not item_type or not item_id:
        logger.warning(f"Fulfillment aborted: Missing student or item information for session {session_id}")
        return False

    amount_total = Decimal(str(session_dict.get('amount_total') or getattr(session, 'amount_total', 0) or 0)) / Decimal('100.0')

    # Fulfill Course Enrollment
    if item_type == 'course':
        course = Course.objects.filter(id=item_id).first()
        if not course:
            logger.error(f"Course ID {item_id} not found during fulfillment.")
            return False

        enrollment, created = CourseEnrollment.objects.get_or_create(
            student=student,
            course=course,
            defaults={
                'status': 'enrolled',
                'payment_status': 'paid',
                'payment_method': 'stripe',
                'amount_paid': amount_total or course.fee,
                'currency': course.currency or '£',
                'order_id': session_id,
            }
        )

        needs_save = False
        if not created:
            if enrollment.payment_status != 'paid':
                enrollment.payment_status = 'paid'
                needs_save = True
            if enrollment.status != 'enrolled' and enrollment.status != 'completed':
                enrollment.status = 'enrolled'
                needs_save = True
            if not enrollment.order_id:
                enrollment.order_id = session_id
                needs_save = True
            if enrollment.amount_paid <= 0:
                enrollment.amount_paid = amount_total or course.fee
                needs_save = True
            if enrollment.is_deleted:
                enrollment.is_deleted = False
                needs_save = True

        if created or needs_save:
            enrollment.save()
            course.enrolled_count += 1
            course.save(update_fields=['enrolled_count'])

        # Send enrollment receipt email
        if not enrollment.receipt_emailed:
            send_course_enrollment_receipt_email(enrollment, request=request)

        # Update transaction
        if transaction:
            transaction.status = 'succeeded'
            transaction.stripe_payment_intent_id = str(payment_intent or '')
            transaction.completed_at = timezone.now()
            transaction.receipt_number = enrollment.receipt_number
            transaction.save(update_fields=['status', 'stripe_payment_intent_id', 'completed_at', 'receipt_number'])

        return True

    # Fulfill Resource Purchase
    elif item_type == 'resource':
        resource = PaidResource.objects.filter(id=item_id).first()
        if not resource:
            logger.error(f"PaidResource ID {item_id} not found during fulfillment.")
            return False

        purchase, created = ResourcePurchase.objects.get_or_create(
            student=student,
            resource=resource,
            defaults={
                'amount_paid': amount_total or resource.price,
                'currency': resource.currency or '£',
                'order_id': session_id,
                'status': 'active',
                'payment_status': 'paid',
                'payment_method': 'stripe',
            }
        )

        needs_save = False
        if not created:
            if purchase.payment_status != 'paid':
                purchase.payment_status = 'paid'
                needs_save = True
            if purchase.status != 'active':
                purchase.status = 'active'
                needs_save = True
            if purchase.is_deleted:
                purchase.is_deleted = False
                needs_save = True
            if not purchase.order_id:
                purchase.order_id = session_id
                needs_save = True
            if purchase.amount_paid <= 0:
                purchase.amount_paid = amount_total or resource.price
                needs_save = True

        if created or needs_save:
            purchase.save()

        # Send purchase receipt email
        if not purchase.receipt_emailed:
            send_purchase_receipt_email(purchase, request=request)

        # Update transaction
        if transaction:
            transaction.status = 'succeeded'
            transaction.stripe_payment_intent_id = str(payment_intent or '')
            transaction.completed_at = timezone.now()
            transaction.receipt_number = purchase.receipt_number
            transaction.save(update_fields=['status', 'stripe_payment_intent_id', 'completed_at', 'receipt_number'])

        return True

    return False


class PaymentConfigView(APIView):
    """
    Returns public Stripe configuration (publishable key and currency)
    so frontends can initialize Stripe Checkout or Elements dynamically.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['USER SIDE - Stripe Payments & Checkout'],
        summary="Get Stripe Public Configuration",
        description="Returns Stripe publishable key and base currency for frontend integration.",
        responses={200: PaymentConfigSerializer}
    )
    def get(self, request):
        return Response({
            'publishable_key': getattr(settings, 'STRIPE_PUBLISHABLE_KEY', '') or os.getenv('STRIPE_PUBLISHABLE_KEY', ''),
            'currency': (getattr(settings, 'STRIPE_CURRENCY', '') or os.getenv('STRIPE_CURRENCY', 'gbp')).lower(),
        }, status=status.HTTP_200_OK)


class CreateCheckoutSessionView(APIView):
    """
    Initiates a Stripe Checkout Session for either a Study Resource or a Course Enrollment.
    Returns the session URL for the frontend to redirect the student to Stripe.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['USER SIDE - Stripe Payments & Checkout'],
        summary="Create Stripe Checkout Session",
        description="Creates a hosted Stripe Checkout Session for purchasing a Course or Study Resource.",
        request=CreateCheckoutSessionSerializer,
        responses={
            201: CheckoutSessionResponseSerializer,
            400: OpenApiResponse(description="Invalid request or student already enrolled"),
            404: OpenApiResponse(description="Course or Resource not found"),
            500: OpenApiResponse(description="Stripe API configuration error")
        }
    )
    def post(self, request):
        serializer = CreateCheckoutSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        item_type = serializer.validated_data['item_type']
        item_lookup = str(serializer.validated_data['item_id']).strip()
        name_input = (serializer.validated_data.get('name') or '').strip()
        phone_input = (serializer.validated_data.get('phone') or '').strip()

        # Resolve student profile
        student = getattr(request.user, 'student_profile', None)
        if not student:
            student, _ = Student.objects.get_or_create(
                email=request.user.email,
                defaults={
                    'user': request.user,
                    'name': name_input or request.user.display_name,
                    'phone': phone_input,
                    'status': 'active'
                }
            )
        else:
            updated_fields = []
            if name_input and (not student.name or student.name == student.email):
                student.name = name_input
                updated_fields.append('name')
            if phone_input and not student.phone:
                student.phone = phone_input
                updated_fields.append('phone')
            if updated_fields:
                student.save(update_fields=updated_fields)

        stripe_secret = getattr(settings, 'STRIPE_SECRET_KEY', '') or os.getenv('STRIPE_SECRET_KEY', '')
        if not stripe_secret:
            return Response(
                {"detail": "Stripe secret key is not configured on the server. Please check .env settings."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        stripe.api_key = stripe_secret

        item_title = ""
        item_obj = None
        amount = Decimal('0.00')
        raw_currency = '£'

        frontend_base = getattr(settings, 'FRONTEND_URL', 'https://avemaria-frontend.vercel.app').rstrip('/')

        # 1. Handle Course
        if item_type == 'course':
            if item_lookup.isdigit():
                item_obj = Course.objects.filter(id=int(item_lookup), is_deleted=False).first()
            if not item_obj:
                try:
                    c_uuid = uuid.UUID(item_lookup)
                    item_obj = Course.objects.filter(uuid=c_uuid, is_deleted=False).first()
                except (ValueError, TypeError, AttributeError):
                    pass
            if not item_obj:
                item_obj = Course.objects.filter(slug=item_lookup, is_deleted=False).first()

            if not item_obj:
                return Response({"detail": "Course not found or is unavailable."}, status=status.HTTP_404_NOT_FOUND)

            # Check if student is already enrolled with paid status
            existing_enrollment = CourseEnrollment.objects.filter(
                student=student, course=item_obj, is_deleted=False
            ).first()
            if existing_enrollment and existing_enrollment.payment_status == 'paid':
                return Response(
                    {"detail": f"You are already enrolled in '{item_obj.title}'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            item_title = item_obj.title
            amount = item_obj.fee
            raw_currency = item_obj.currency

        # 2. Handle Resource
        elif item_type == 'resource':
            if item_lookup.isdigit():
                item_obj = PaidResource.objects.filter(id=int(item_lookup), is_deleted=False).first()
            if not item_obj:
                try:
                    r_uuid = uuid.UUID(item_lookup)
                    item_obj = PaidResource.objects.filter(uuid=r_uuid, is_deleted=False).first()
                except (ValueError, TypeError, AttributeError):
                    pass
            if not item_obj:
                item_obj = PaidResource.objects.filter(slug=item_lookup, is_deleted=False).first()

            if not item_obj:
                return Response({"detail": "Study Resource not found or is unavailable."}, status=status.HTTP_404_NOT_FOUND)

            # Check if student already purchased
            existing_purchase = ResourcePurchase.objects.filter(
                student=student, resource=item_obj, is_deleted=False
            ).first()
            if existing_purchase and existing_purchase.payment_status == 'paid':
                return Response(
                    {"detail": f"You have already purchased '{item_obj.title}'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            item_title = item_obj.title
            amount = item_obj.price
            raw_currency = item_obj.currency

        if amount <= 0:
            return Response(
                {"detail": "This item is complimentary / free. No payment required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        iso_currency = get_stripe_currency(raw_currency)
        unit_amount_cents = int(round(float(amount) * 100))

        # Record initial pending transaction
        transaction = PaymentTransaction.objects.create(
            student=student,
            item_type=item_type,
            item_id=item_obj.id,
            item_title=item_title,
            amount=amount,
            currency=iso_currency,
            status='pending',
            stripe_customer_email=student.email,
        )

        frontend_base = getattr(settings, 'FRONTEND_URL', 'https://avemaria-frontend.vercel.app').rstrip('/')
        if not frontend_base.startswith(('http://', 'https://')):
            frontend_base = f"https://{frontend_base}"

        raw_success_url = (serializer.validated_data.get('success_url') or '').strip()
        if raw_success_url:
            if not raw_success_url.startswith(('http://', 'https://')):
                success_url = f"{frontend_base}/{raw_success_url.lstrip('/')}"
            else:
                success_url = raw_success_url
        else:
            success_url = (
                f"{frontend_base}/payment/success?session_id={{CHECKOUT_SESSION_ID}}&item_type={item_type}&item_id={item_obj.id}"
            )

        raw_cancel_url = (serializer.validated_data.get('cancel_url') or '').strip()
        if raw_cancel_url:
            if not raw_cancel_url.startswith(('http://', 'https://')):
                cancel_url = f"{frontend_base}/{raw_cancel_url.lstrip('/')}"
            else:
                cancel_url = raw_cancel_url
        else:
            cancel_url = (
                f"{frontend_base}/payment/cancel?item_type={item_type}&item_id={item_obj.id}"
            )

        try:
            checkout_session = stripe.checkout.Session.create(
                line_items=[{
                    'price_data': {
                        'currency': iso_currency,
                        'unit_amount': unit_amount_cents,
                        'product_data': {
                            'name': item_title,
                            'description': f"Avemaria {item_type.title()} Registration & Access",
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                customer_email=student.email,
                client_reference_id=str(student.id),
                metadata={
                    'transaction_id': str(transaction.id),
                    'student_id': str(student.id),
                    'item_type': item_type,
                    'item_id': str(item_obj.id),
                    'student_name': str(student.name or ''),
                    'student_phone': str(student.phone or ''),
                },
                success_url=success_url,
                cancel_url=cancel_url,
            )

            transaction.stripe_session_id = checkout_session.id
            transaction.save(update_fields=['stripe_session_id'])

            return Response({
                'url': checkout_session.url,
                'checkout_url': checkout_session.url,
                'checkoutUrl': checkout_session.url,
                'session_url': checkout_session.url,
                'session_id': checkout_session.id,
                'sessionId': checkout_session.id,
                'id': checkout_session.id,
                'publishable_key': getattr(settings, 'STRIPE_PUBLISHABLE_KEY', '') or os.getenv('STRIPE_PUBLISHABLE_KEY', ''),
                'item_type': item_type,
                'item_id': str(item_obj.uuid),
                'item_title': item_title,
                'amount': float(amount),
                'currency': iso_currency.upper(),
            }, status=status.HTTP_201_CREATED)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating session: {str(e)}")
            transaction.status = 'failed'
            transaction.save(update_fields=['status'])
            return Response(
                {"detail": f"Stripe gateway error: {e.user_message or str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception("Unexpected error in CreateCheckoutSessionView")
            transaction.status = 'failed'
            transaction.save(update_fields=['status'])
            return Response(
                {"detail": f"Failed to initialize checkout session: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    """
    Public webhook receiver for Stripe asynchronous events.
    Verifies event signature using STRIPE_WEBHOOK_SECRET and fulfills
    course enrollments and resource purchases.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['USER SIDE - Stripe Payments & Checkout'],
        summary="Stripe Webhook Listener",
        description="Receives and processes incoming events sent by Stripe (checkout.session.completed, payment_failed).",
        request=StripeWebhookPayloadSerializer,
        responses={200: OpenApiResponse(description="Webhook handled successfully")}
    )
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '') or os.getenv('STRIPE_WEBHOOK_SECRET', '')

        event = None

        if webhook_secret:
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, webhook_secret
                )
            except ValueError as e:
                logger.error(f"Invalid webhook payload: {str(e)}")
                return Response({"detail": "Invalid payload"}, status=status.HTTP_400_BAD_REQUEST)
            except stripe.error.SignatureVerificationError as e:
                logger.error(f"Invalid webhook signature: {str(e)}")
                return Response({"detail": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # If webhook secret is not set yet in development, parse raw json
            try:
                data = json.loads(payload.decode('utf-8'))
                event = stripe.Event.construct_from(data, stripe.api_key)
            except Exception as e:
                logger.error(f"Failed parsing webhook JSON: {str(e)}")
                return Response({"detail": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)

        event_dict = stripe_to_dict(event)
        event_type = event_dict.get('type')
        data_object = stripe_to_dict(event_dict.get('data', {}).get('object', {}))

        logger.info(f"Received Stripe event: {event_type}")

        # 1. Checkout session completed
        if event_type == 'checkout.session.completed':
            fulfill_checkout_session(data_object, request=request)

        # 2. Payment intent failed
        elif event_type == 'payment_intent.payment_failed':
            session_id = data_object.get('id')
            tx = PaymentTransaction.objects.filter(
                stripe_payment_intent_id=session_id
            ).first()
            if tx:
                tx.status = 'failed'
                tx.save(update_fields=['status'])

        return Response({"status": "success"}, status=status.HTTP_200_OK)


class VerifySessionView(APIView):
    """
    Immediate frontend verification endpoint.
    When a student is redirected to /payment/success?session_id=..., the frontend
    calls this endpoint to verify payment and retrieve purchase/enrollment receipt details.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['USER SIDE - Stripe Payments & Checkout'],
        summary="Verify Stripe Checkout Session",
        description="Checks session status directly against Stripe API and ensures fulfillment has occurred.",
        parameters=[
            OpenApiParameter('session_id', str, OpenApiParameter.QUERY, required=True, description="Stripe Checkout Session ID")
        ],
        responses={200: VerifySessionResponseSerializer}
    )
    def get(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({"detail": "Parameter 'session_id' is required."}, status=status.HTTP_400_BAD_REQUEST)

        stripe_secret = getattr(settings, 'STRIPE_SECRET_KEY', '') or os.getenv('STRIPE_SECRET_KEY', '')
        if not stripe_secret:
            return Response(
                {"detail": "Stripe is not configured on the server."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        stripe.api_key = stripe_secret

        try:
            session = stripe.checkout.Session.retrieve(session_id)
            session_dict = stripe_to_dict(session)

            payment_status = session_dict.get('payment_status') or getattr(session, 'payment_status', 'unpaid')

            metadata = stripe_to_dict(session_dict.get('metadata')) or stripe_to_dict(getattr(session, 'metadata', None))
            item_type = metadata.get('item_type', '')
            raw_item_id = metadata.get('item_id')
            item_id = int(raw_item_id) if raw_item_id and str(raw_item_id).isdigit() else None

            item_title = ""
            receipt_number = ""
            amount_paid = float(session_dict.get('amount_total') or getattr(session, 'amount_total', 0) or 0) / 100.0
            currency = str(session_dict.get('currency') or getattr(session, 'currency', 'gbp')).upper()

            if payment_status == 'paid':
                # Run fulfillment idempotently
                fulfill_checkout_session(session, request=request)

                tx = PaymentTransaction.objects.filter(stripe_session_id=session_id).first()
                if tx:
                    item_title = tx.item_title
                    receipt_number = tx.receipt_number

                if not receipt_number:
                    if item_type == 'course' and item_id:
                        enr = CourseEnrollment.objects.filter(course_id=item_id, order_id=session_id).first()
                        if enr:
                            receipt_number = enr.receipt_number
                            item_title = enr.course.title
                    elif item_type == 'resource' and item_id:
                        pur = ResourcePurchase.objects.filter(resource_id=item_id, order_id=session_id).first()
                        if pur:
                            receipt_number = pur.receipt_number
                            item_title = pur.resource.title

            item_uuid = None
            if item_type == 'course':
                c = None
                if item_id:
                    c = Course.objects.filter(id=item_id).first()
                elif raw_item_id:
                    try:
                        u = uuid.UUID(str(raw_item_id))
                        c = Course.objects.filter(uuid=u).first()
                    except (ValueError, TypeError):
                        pass
                if c:
                    item_uuid = str(c.uuid)
            elif item_type == 'resource':
                r = None
                if item_id:
                    r = PaidResource.objects.filter(id=item_id).first()
                elif raw_item_id:
                    try:
                        u = uuid.UUID(str(raw_item_id))
                        r = PaidResource.objects.filter(uuid=u).first()
                    except (ValueError, TypeError):
                        pass
                if r:
                    item_uuid = str(r.uuid)

            return Response({
                'status': payment_status,
                'item_type': item_type,
                'item_id': item_uuid or (str(item_id) if item_id else (str(raw_item_id) if raw_item_id else '')),
                'item_title': item_title,
                'receipt_number': receipt_number,
                'amount_paid': amount_paid,
                'currency': currency,
            }, status=status.HTTP_200_OK)

        except stripe.error.StripeError as e:
            return Response({"detail": f"Stripe error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": f"Failed to verify session: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StudentPaymentTransactionsView(APIView):
    """
    Returns the authenticated student's payment transactions history.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['USER SIDE - Stripe Payments & Checkout'],
        summary="List Student Payment Transactions",
        description="Returns list of all Stripe payment attempts and transactions for the logged-in student.",
        responses={200: PaymentTransactionSerializer(many=True)}
    )
    def get(self, request):
        student = getattr(request.user, 'student_profile', None)
        if not student and getattr(request.user, 'email', None):
            student = Student.objects.filter(email__iexact=request.user.email, is_deleted=False).first()

        is_admin = getattr(request.user, 'is_staff', False) or getattr(request.user, 'role', None) == 'admin'
        if not student and not is_admin:
            return Response([], status=status.HTTP_200_OK)

        if is_admin:
            transactions = PaymentTransaction.objects.all().order_by('-created_at')
        else:
            transactions = PaymentTransaction.objects.filter(student=student).order_by('-created_at')
        serializer = PaymentTransactionSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StudentPaymentTransactionDetailView(APIView):
    """
    Retrieves full transaction details for a single payment by ID or UUID.
    Supports lookup by PaymentTransaction UUID, integer ID, Stripe session ID,
    receipt number, or ResourcePurchase/CourseEnrollment UUID.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentTransactionDetailSerializer

    @extend_schema(
        tags=['USER SIDE - Stripe Payments & Checkout'],
        summary="Get Single Payment Transaction Detail",
        description="Retrieves comprehensive details of a single transaction by ID, UUID, Stripe session ID, or receipt number.",
        parameters=[
            OpenApiParameter('id', str, OpenApiParameter.PATH, description="Transaction ID, UUID, Session ID, or Receipt Number")
        ],
        responses={
            200: PaymentTransactionDetailSerializer,
            404: OpenApiResponse(description="Transaction not found")
        }
    )
    def get(self, request, id):
        student = getattr(request.user, 'student_profile', None)
        if not student and getattr(request.user, 'email', None):
            student = Student.objects.filter(email__iexact=request.user.email, is_deleted=False).first()

        is_admin = getattr(request.user, 'is_staff', False) or getattr(request.user, 'role', None) == 'admin'
        if not student and not is_admin:
            return Response({"detail": "Student profile not found."}, status=status.HTTP_404_NOT_FOUND)

        lookup = str(id).strip()
        parsed_uuid = None
        try:
            parsed_uuid = uuid.UUID(lookup)
        except (ValueError, TypeError, AttributeError):
            pass

        # 1. Look up PaymentTransaction directly
        qs = PaymentTransaction.objects.all() if is_admin else PaymentTransaction.objects.filter(student=student)
        tx = None

        if parsed_uuid:
            tx = qs.filter(uuid=parsed_uuid).first()

        if not tx and lookup.isdigit():
            tx = qs.filter(id=int(lookup)).first()

        if not tx:
            tx = qs.filter(stripe_session_id=lookup).first()

        if not tx:
            tx = qs.filter(receipt_number__iexact=lookup).first()

        # 2. Check ResourcePurchase or CourseEnrollment if queried with their UUID
        if not tx and parsed_uuid:
            pur_qs = ResourcePurchase.objects.all() if is_admin else ResourcePurchase.objects.filter(student=student)
            purchase = pur_qs.filter(uuid=parsed_uuid, is_deleted=False).first()
            if purchase:
                if purchase.order_id:
                    tx = qs.filter(stripe_session_id=purchase.order_id).first()
                if not tx and purchase.receipt_number:
                    tx = qs.filter(receipt_number=purchase.receipt_number).first()
                if not tx:
                    tx, _ = PaymentTransaction.objects.get_or_create(
                        student=purchase.student,
                        item_type='resource',
                        item_id=purchase.resource_id,
                        defaults={
                            'item_title': purchase.resource.title if purchase.resource else 'Study Resource',
                            'amount': purchase.amount_paid or (purchase.resource.price if purchase.resource else Decimal('0.00')),
                            'currency': get_stripe_currency(purchase.currency),
                            'status': 'succeeded' if purchase.payment_status == 'paid' else purchase.payment_status,
                            'stripe_session_id': purchase.order_id or '',
                            'receipt_number': purchase.receipt_number or '',
                            'completed_at': purchase.purchased_at or purchase.created_at,
                        }
                    )

            if not tx:
                enr_qs = CourseEnrollment.objects.all() if is_admin else CourseEnrollment.objects.filter(student=student)
                enrollment = enr_qs.filter(uuid=parsed_uuid, is_deleted=False).first()
                if enrollment:
                    if enrollment.order_id:
                        tx = qs.filter(stripe_session_id=enrollment.order_id).first()
                    if not tx and enrollment.receipt_number:
                        tx = qs.filter(receipt_number=enrollment.receipt_number).first()
                    if not tx:
                        tx, _ = PaymentTransaction.objects.get_or_create(
                            student=enrollment.student,
                            item_type='course',
                            item_id=enrollment.course_id,
                            defaults={
                                'item_title': enrollment.course.title if enrollment.course else 'Course',
                                'amount': enrollment.amount_paid or (enrollment.course.fee if enrollment.course else Decimal('0.00')),
                                'currency': get_stripe_currency(enrollment.currency),
                                'status': 'succeeded' if enrollment.payment_status == 'paid' else enrollment.payment_status,
                                'stripe_session_id': enrollment.order_id or '',
                                'receipt_number': enrollment.receipt_number or '',
                                'completed_at': enrollment.enrolled_at or enrollment.created_at,
                            }
                        )

        if not tx:
            return Response(
                {"detail": f"Payment transaction '{id}' not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PaymentTransactionDetailSerializer(tx)
        return Response(serializer.data, status=status.HTTP_200_OK)