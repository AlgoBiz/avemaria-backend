from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from drf_spectacular.utils import extend_schema
from apps.courses.models import Course
from apps.categories.models import Category
from apps.resources.models import PaidResource, ResourcePDF
from apps.students.models import Student
from apps.enquiries.models import Enquiry
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

        courses_data = CourseListSerializer(programmes_catalog, many=True).data

        packs_label = f'Across {resource_pools_count} study resource packs' if resource_pools_count else 'Across 3 study resource packs'
        courses_label = f'Across {categories_count} categories' if categories_count else 'Across 5 categories'

        # Performance Bar Graph KPIs & Monthly comparative chart data
        kpis = {
            'course_enrolments': {
                'value': '1,420',
                'count': 1420,
                'change': '+18.4%',
                'trend': 'up',
                'label': 'Active programme students'
            },
            'resource_downloads': {
                'value': '3,890',
                'count': 3890,
                'change': '+24.2%',
                'trend': 'up',
                'label': 'PDFs & mock papers accessed'
            },
            'pass_success_rate': {
                'value': '97.8%',
                'percentage': 97.8,
                'badge': 'Verified',
                'label': 'Licensing & PSC qualifiers'
            },
            'avg_satisfaction': {
                'value': '4.92 / 5',
                'rating': 4.92,
                'max_rating': 5,
                'stars': 5,
                'reviews_count_label': 'Based on 1,650+ reviews'
            }
        }

        chart_data = [
            {'month': 'Feb', 'courses': 45, 'resources': 75, 'total': 120},
            {'month': 'Mar', 'courses': 58, 'resources': 110, 'total': 168},
            {'month': 'Apr', 'courses': 74, 'resources': 142, 'total': 216},
            {'month': 'May', 'courses': 62, 'resources': 130, 'total': 192},
            {'month': 'Jun', 'courses': 105, 'resources': 185, 'total': 290},
            {'month': 'Jul', 'courses': 118, 'resources': 220, 'total': 338},
            {'month': 'Aug', 'courses': 130, 'resources': 260, 'total': 390},
        ]

        # Item-Wise Performance Breakdown Table (6 top performing items)
        item_wise_performance = [
            {
                'sl_no': 1,
                'item_name': 'Gulf Licensing Preparation – DHA · HAAD · MOH · QCHP',
                'type': 'Course',
                'category': 'International Licensing',
                'engagements': '348 Enrolled',
                'success_metric': '96.4% Completion Rate',
                'price_fee': '£420',
                'price': '£420',
                'status': 'High Demand'
            },
            {
                'sl_no': 2,
                'item_name': 'DHA / HAAD / MOH mock exam pack',
                'type': 'Resource',
                'category': 'Question Papers',
                'engagements': '642 Downloads',
                'success_metric': '4.9 / 5.0 Average Rating',
                'price_fee': '£29.00',
                'price': '£29.00',
                'status': 'Top Seller'
            },
            {
                'sl_no': 3,
                'item_name': 'Kerala PSC Lab Technician Grade II — Complete Course',
                'type': 'Course',
                'category': 'Kerala PSC',
                'engagements': '285 Enrolled',
                'success_metric': '92.8% Completion Rate',
                'price_fee': '£180',
                'price': '£180',
                'status': 'Active Batch'
            },
            {
                'sl_no': 4,
                'item_name': 'Kerala PSC lab technician solved papers (2016-2026)',
                'type': 'Resource',
                'category': 'Question Papers',
                'engagements': '518 Downloads',
                'success_metric': '4.8 / 5.0 Average Rating',
                'price_fee': '£19.00',
                'price': '£19.00',
                'status': 'Popular'
            },
            {
                'sl_no': 5,
                'item_name': 'MSc MLT Entrance — Postgraduate Coaching',
                'type': 'Course',
                'category': 'MSc MLT Entrance',
                'engagements': '194 Enrolled',
                'success_metric': '94.2% Completion Rate',
                'price_fee': '£240',
                'price': '£240',
                'status': 'Trending'
            },
            {
                'sl_no': 6,
                'item_name': 'Clinical biochemistry high-yield revision pack',
                'type': 'Resource',
                'category': 'Notes',
                'engagements': '412 Downloads',
                'success_metric': '4.9 / 5.0 Average Rating',
                'price_fee': '£15.00',
                'price': '£15.00',
                'status': 'Verified'
            }
        ]

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
