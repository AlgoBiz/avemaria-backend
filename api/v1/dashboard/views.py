from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from apps.courses.models import Course
from apps.categories.models import Category
from apps.resources.models import PaidResource, ResourcePDF
from apps.students.models import Student
from apps.enquiries.models import Enquiry
from api.v1.enquiries.serializers import EnquiryAdminSerializer
from api.v1.courses.serializers import CourseListSerializer

class DashboardOverviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

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

        courses_data = CourseListSerializer(programmes_catalog, many=True).data

        pools_label = f'Across {resource_pools_count} study resource pools' if resource_pools_count else 'Across study resource pools'
        courses_label = f'Across {categories_count} categories' if categories_count else 'Across all categories'

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
                    'label': pools_label
                }
            },
            'new_enquiries_count': new_enquiries_count,
            'total_enquiries': total_enquiries,
            'recent_enquiries': enquiries_data,
            'programmes_catalog': courses_data,
            'quick_shortcuts': [
                {'title': 'Course Manager', 'description': 'Edit fees, curriculum, duration', 'link': '/admin/courses'},
                {'title': 'Categories', 'description': 'Organise programme sectors', 'link': '/admin/categories'},
                {'title': 'Paid Resources', 'description': 'Manage study packs & question papers', 'link': '/admin/resources'},
                {'title': 'Success Stories', 'description': 'Review student passes & quotes', 'link': '/admin/testimonials'},
            ]
        }
        return Response(data)
