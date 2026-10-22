import calendar
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Count, Sum, Q, Avg
from drf_spectacular.utils import extend_schema
from apps.courses.models import Course, CourseEnrollment
from apps.categories.models import Category
from apps.resources.models import PaidResource, ResourcePDF, ResourcePurchase
from apps.students.models import Student
from apps.enquiries.models import Enquiry
from apps.testimonials.models import Testimonial
from api.v1.enquiries.serializers import EnquiryAdminSerializer
from api.v1.courses.serializers import CourseListSerializer
from .serializers import DashboardOverviewResponseSerializer

class DashboardOverviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DashboardOverviewResponseSerializer

    @extend_schema(
        tags=['Admin Dashboard'],
        summary="Admin Dashboard Overview KPIs, Analytics & Catalog",
        description="Returns total user counts, active courses, recent enquiries, catalog items, performance KPIs, monthly trends, and top items.",
        responses={200: DashboardOverviewResponseSerializer}
    )
    def get(self, request):
        total_users = Student.objects.filter(is_deleted=False).count()
        total_courses = Course.objects.filter(is_published=True, is_deleted=False).count()
        active_users = Student.objects.filter(status='active', is_deleted=False).count()
        total_documents_uploaded = ResourcePDF.objects.filter(is_deleted=False).count()
        categories_count = Category.objects.filter(is_deleted=False).count()
        resource_pools_count = PaidResource.objects.filter(is_deleted=False).count()

        new_enquiries_count = Enquiry.objects.filter(status='new', is_deleted=False).count()
        total_enquiries = Enquiry.objects.filter(is_deleted=False).count()

        # Newly added enquiries and courses appear first (-created_at, -id)
        recent_enquiries = Enquiry.objects.filter(is_deleted=False)[:5]
        programmes_catalog = Course.objects.filter(is_published=True, is_deleted=False).order_by('-is_featured', '-created_at', '-id')[:5]

        enquiries_data = EnquiryAdminSerializer(recent_enquiries, many=True).data
        for idx, item in enumerate(enquiries_data, start=1):
            item['sl_no'] = idx
            item['date'] = item.get('received_date_formatted', '')
            item['candidate'] = {
                'name': item.get('candidate_name', ''),
                'email': item.get('email', '')
            }
            item['course_topic'] = item.get('topic', '')

        courses_data = CourseListSerializer(programmes_catalog, many=True, context={'request': request}).data
        for item in courses_data:
            item['fee_formatted'] = item.get('fee', '')
            dur = item.get('duration', '')
            mode = item.get('learning_mode', '')
            parts = [p for p in [dur, mode.capitalize() if mode else ''] if p]
            item['schedule_display'] = ' • '.join(parts)

        packs_label = f'Across {resource_pools_count} study resource pack{"s" if resource_pools_count != 1 else ""}'
        courses_label = f'Across {categories_count} categor{"ies" if categories_count != 1 else "y"}'

        now = timezone.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if current_month_start.month == 1:
            prev_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
        else:
            prev_month_start = current_month_start.replace(month=current_month_start.month - 1)

        # 1. Course Enrolments
        total_course_enrollments = CourseEnrollment.objects.filter(is_deleted=False).count()
        this_month_enr = CourseEnrollment.objects.filter(
            is_deleted=False,
            enrolled_at__gte=current_month_start
        ).count()
        prev_month_enr = CourseEnrollment.objects.filter(
            is_deleted=False,
            enrolled_at__gte=prev_month_start,
            enrolled_at__lt=current_month_start
        ).count()

        if prev_month_enr > 0:
            enr_change = ((this_month_enr - prev_month_enr) / prev_month_enr) * 100
            enr_change_str = f"{enr_change:+.1f}%"
            enr_trend = 'up' if enr_change >= 0 else 'down'
        elif this_month_enr > 0:
            enr_change_str = '+100.0%'
            enr_trend = 'up'
        else:
            enr_change_str = '+0.0%'
            enr_trend = 'up'

        # 2. Resource Downloads & Purchases
        purchases_agg = ResourcePurchase.objects.filter(is_deleted=False).aggregate(
            total_dl=Sum('download_count'),
            total_purchases=Count('id')
        )
        total_downloads = purchases_agg['total_dl'] or 0
        total_purchases = purchases_agg['total_purchases'] or 0
        total_resource_activity = max(total_downloads, total_purchases)

        this_month_purchases = ResourcePurchase.objects.filter(
            is_deleted=False,
            purchased_at__gte=current_month_start
        ).count()
        prev_month_purchases = ResourcePurchase.objects.filter(
            is_deleted=False,
            purchased_at__gte=prev_month_start,
            purchased_at__lt=current_month_start
        ).count()

        if prev_month_purchases > 0:
            dl_change = ((this_month_purchases - prev_month_purchases) / prev_month_purchases) * 100
            dl_change_str = f"{dl_change:+.1f}%"
            dl_trend = 'up' if dl_change >= 0 else 'down'
        elif this_month_purchases > 0:
            dl_change_str = '+100.0%'
            dl_trend = 'up'
        else:
            dl_change_str = '+0.0%'
            dl_trend = 'up'

        # 3. Pass Success Rate
        completed_enrollments_count = CourseEnrollment.objects.filter(is_deleted=False, status='completed').count()
        if total_course_enrollments > 0:
            pass_rate = round((completed_enrollments_count / total_course_enrollments) * 100, 1)
        else:
            pass_rate = 0.0

        # 4. Average Satisfaction Rating
        testimonial_stats = Testimonial.objects.filter(is_active=True, is_deleted=False).aggregate(
            avg_rating=Avg('rating'),
            count=Count('id')
        )
        avg_satisfaction_rating = round(testimonial_stats['avg_rating'] or 0.0, 2)
        reviews_count = testimonial_stats['count'] or 0
        stars_count = int(round(avg_satisfaction_rating)) if avg_satisfaction_rating > 0 else 0
        reviews_label = f"Based on {reviews_count} review{'s' if reviews_count != 1 else ''}" if reviews_count > 0 else "Based on 0 reviews"

        kpis = {
            'course_enrolments': {
                'value': f"{total_course_enrollments:,}",
                'count': total_course_enrollments,
                'change': enr_change_str,
                'trend': enr_trend,
                'label': 'Active programme students'
            },
            'resource_downloads': {
                'value': f"{total_resource_activity:,}",
                'count': total_resource_activity,
                'change': dl_change_str,
                'trend': dl_trend,
                'label': 'PDFs & mock papers accessed'
            },
            'pass_success_rate': {
                'value': f"{pass_rate}%",
                'percentage': pass_rate,
                'badge': 'Verified' if pass_rate >= 50 else 'Normal',
                'label': 'Licensing & PSC qualifiers'
            },
            'avg_satisfaction': {
                'value': f"{avg_satisfaction_rating:.2f} / 5" if reviews_count > 0 else "0.0 / 5",
                'rating': avg_satisfaction_rating,
                'max_rating': 5,
                'stars': stars_count,
                'reviews_count_label': reviews_label
            }
        }

        # Dynamic monthly comparative chart data for the last 7 months
        chart_data = []
        for i in range(6, -1, -1):
            y = now.year
            m = now.month - i
            while m <= 0:
                m += 12
                y -= 1

            month_name = calendar.month_abbr[m]

            m_courses = CourseEnrollment.objects.filter(
                is_deleted=False,
                enrolled_at__year=y,
                enrolled_at__month=m
            ).count()

            m_resources = ResourcePurchase.objects.filter(
                is_deleted=False,
                purchased_at__year=y,
                purchased_at__month=m
            ).count()

            chart_data.append({
                'month': month_name,
                'courses': m_courses,
                'resources': m_resources,
                'total': m_courses + m_resources
            })

        # Dynamic Item-Wise Performance Breakdown (Top performing courses and resources from database)
        courses_qs = Course.objects.filter(is_deleted=False).select_related('category').annotate(
            actual_enrollments=Count('enrollments', filter=Q(enrollments__is_deleted=False)),
            completed_enrollments=Count('enrollments', filter=Q(enrollments__is_deleted=False, enrollments__status='completed'))
        ).order_by('-is_featured', '-enrolled_count', '-actual_enrollments', '-created_at')

        resources_qs = PaidResource.objects.filter(is_deleted=False).annotate(
            purchases_count=Count('purchases', filter=Q(purchases__is_deleted=False)),
            total_downloads=Sum('purchases__download_count', filter=Q(purchases__is_deleted=False))
        ).order_by('-total_downloads', '-purchases_count', '-created_at')

        avg_t = testimonial_stats['avg_rating']
        resource_rating_str = f"{round(avg_t, 1):.1f} / 5.0 Average Rating" if avg_t else "No ratings yet"

        course_items = []
        for course in courses_qs[:10]:
            enrolled_num = max(course.enrolled_count or 0, getattr(course, 'actual_enrollments', 0))
            tot_enr = getattr(course, 'actual_enrollments', 0)
            comp_enr = getattr(course, 'completed_enrollments', 0)
            if tot_enr > 0 and comp_enr > 0:
                rate = round((comp_enr / tot_enr) * 100, 1)
                success_metric = f"{rate}% Completion Rate"
            elif course.rating:
                success_metric = f"{course.rating} / 5.0 Average Rating"
            elif tot_enr > 0:
                success_metric = f"{tot_enr} Active Learner{'s' if tot_enr != 1 else ''}"
            else:
                success_metric = "No ratings yet"

            curr = course.currency if course.currency and course.currency not in ['', '?', ''] else '£'
            if course.fee is not None:
                fee_val = int(course.fee) if course.fee == int(course.fee) else course.fee
                price_str = f"{curr}{fee_val}"
            else:
                price_str = f"{curr}0"

            if not course.is_published:
                item_status = 'Draft'
            elif course.is_featured:
                item_status = 'High Demand'
            elif enrolled_num >= 50:
                item_status = 'High Demand'
            elif enrolled_num >= 10:
                item_status = 'Popular'
            elif enrolled_num > 0:
                item_status = 'Active Batch'
            else:
                item_status = 'Active Batch'

            category_title = course.category.title if course.category else 'General'

            course_items.append({
                'id': course.id,
                'item_name': course.title,
                'type': 'Course',
                'category': category_title,
                'engagements': f"{enrolled_num} Enrolled",
                'success_metric': success_metric,
                'price_fee': price_str,
                'price': price_str,
                'status': item_status,
            })

        resource_items = []
        for resource in resources_qs[:10]:
            dl_count = getattr(resource, 'total_downloads', 0) or 0
            purchases_num = getattr(resource, 'purchases_count', 0) or 0
            engagements_num = max(dl_count, purchases_num)

            curr = resource.currency if resource.currency and resource.currency not in ['', '?', ''] else '£'
            if resource.price is not None:
                if resource.price == int(resource.price):
                    p_val = f"{int(resource.price)}.00"
                else:
                    p_val = f"{resource.price:.2f}"
                price_str = f"{curr}{p_val}"
            else:
                price_str = f"{curr}0.00"

            if engagements_num >= 50:
                item_status = 'Top Seller'
            elif engagements_num >= 10:
                item_status = 'Popular'
            elif engagements_num > 0:
                item_status = 'Trending'
            else:
                item_status = 'Verified'

            resource_items.append({
                'id': resource.id,
                'item_name': resource.title,
                'type': 'Resource',
                'category': resource.category or 'Question Papers',
                'engagements': f"{engagements_num} Downloads",
                'success_metric': resource_rating_str,
                'price_fee': price_str,
                'price': price_str,
                'status': item_status,
            })

        # Interleave top courses and resources for a balanced overview
        combined = []
        max_count = max(len(course_items), len(resource_items))
        for i in range(max_count):
            if i < len(course_items):
                combined.append(course_items[i])
            if i < len(resource_items):
                combined.append(resource_items[i])

        item_wise_performance = combined[:6]
        for idx, itm in enumerate(item_wise_performance, start=1):
            itm['sl_no'] = idx

        data = {
            'stats': {
                'total_users': {
                    'count': total_users,
                    'label': 'Registered learners & candidates'
                },
                'total_courses': {
                    'count': total_courses,
                    'label': courses_label
                },
                'active_users': {
                    'count': active_users,
                    'label': 'Active on learning portal'
                },
                'total_documents_uploaded': {
                    'count': total_documents_uploaded,
                    'label': packs_label
                }
            },
            'performance_overview': {
                'title': 'Course & Resource Performance Overview',
                'subtitle': 'Monthly comparative bar chart of course admissions versus study pack downloads',
                'kpis': kpis,
                'chart_data': chart_data
            },
            'item_wise_performance': item_wise_performance,
            'new_enquiries_count': new_enquiries_count,
            'total_enquiries': total_enquiries,
            'recent_enquiries': enquiries_data,
            'featured_courses': courses_data,
            'programmes_catalog': courses_data,
            'quick_shortcuts': [
                {'title': 'Course Manager', 'description': 'Edit fees, curriculum, duration', 'link': '/admin/courses'},
                {'title': 'Categories', 'description': 'Organise programme sectors', 'link': '/admin/categories'},
                {'title': 'Paid Resources', 'description': 'Manage study packs & question papers', 'link': '/admin/resources'},
                {'title': 'Success Stories', 'description': 'Review student passes & quotes', 'link': '/admin/testimonials'},
            ]
        }
        return Response(data)
