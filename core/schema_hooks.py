import re


def organize_user_admin_tags(result, generator, request, public):
    """
    Postprocessing hook for drf-spectacular.
    Categorizes all endpoints into either:
      - 'USER SIDE - <Module>' (Student & Public Portal APIs)
      - 'ADMIN SIDE - <Module>' (Admin Management & Dashboard APIs)


    Ensures that tags and paths are grouped and ordered so that all USER SIDE
    endpoints appear in the top section, followed by all ADMIN SIDE endpoints.
    """
    paths = result.get('paths', {})

    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue

            current_tags = operation.get('tags', [])
            new_tags = []

            # 1. Authentication & Profile
            if path.startswith('/api/v1/auth/'):
                if '/student/' in path:
                    if 'profile' in path:
                        new_tags.append('USER SIDE - Student Portal & Profile')
                    elif 'document' in path:
                        new_tags.append('USER SIDE - Student Documents')
                    elif 'course' in path:
                        new_tags.append('USER SIDE - Student Opted Courses')
                    elif any(k in path for k in ['resource', 'purchase']):
                        new_tags.append('USER SIDE - Student Resource Purchases')
                    elif any(k in path for k in ['invoice', 'payment']):
                        new_tags.append('USER SIDE - Student Invoices & Payments')
                    else:
                        new_tags.append('USER SIDE - Authentication')
                elif any(k in path for k in ['/admin/', 'otp', 'change-password']):
                    new_tags.append('ADMIN SIDE - Authentication')
                elif '/profile' in path:
                    new_tags.append('ADMIN SIDE - Admin Profile')
                elif '/token' in path:
                    new_tags.append('USER SIDE - Authentication')
                    new_tags.append('ADMIN SIDE - Authentication')
                else:
                    new_tags.append('ADMIN SIDE - Authentication')

            # 2. Admin Dashboard
            elif path.startswith('/api/v1/dashboard/'):
                new_tags.append('ADMIN SIDE - Dashboard')

            # 3. Portal Settings
            elif path.startswith('/api/v1/settings/'):
                if method.lower() == 'get':
                    new_tags.append('USER SIDE - Portal Settings')
                    new_tags.append('ADMIN SIDE - Portal Settings')
                else:
                    new_tags.append('ADMIN SIDE - Portal Settings')

            # 4. Student Enrolments Register & Candidate Management (Admin)
            elif path.startswith('/api/v1/students/'):
                new_tags.append('ADMIN SIDE - Students & Enrolments')

            # 5. Enquiries & Contact submissions vs Lead management
            elif path.startswith('/api/v1/enquiries/'):
                if any(k in path for k in ['/contact/', '/submit/', '/create/']) or (path == '/api/v1/enquiries/' and method.lower() == 'post'):
                    new_tags.append('USER SIDE - Enquiries & Contact')
                else:
                    new_tags.append('ADMIN SIDE - Enquiries & Leads')

            # 6. Courses
            elif path.startswith('/api/v1/courses/'):
                if method.lower() == 'get':
                    new_tags.append('USER SIDE - Courses')
                    new_tags.append('ADMIN SIDE - Courses')
                else:
                    new_tags.append('ADMIN SIDE - Courses')

            # 7. Resources & Student purchase receipts
            elif path.startswith('/api/v1/resources/'):
                if any(k in path for k in ['purchased', 'purchase-history']):
                    new_tags.append('USER SIDE - Student Resource Purchases')
                elif any(k in path for k in ['receipts', 'payment-details']):
                    new_tags.append('USER SIDE - Student Invoices & Payments')
                elif method.lower() == 'get':
                    new_tags.append('USER SIDE - Resources')
                    new_tags.append('ADMIN SIDE - Resources')
                else:
                    new_tags.append('ADMIN SIDE - Resources')

            # 8. Blogs & Insights
            elif path.startswith('/api/v1/blog') or path.startswith('/api/v1/blogs'):
                if method.lower() == 'get' and not path.endswith('/stats/'):
                    new_tags.append('USER SIDE - Blogs')
                    new_tags.append('ADMIN SIDE - Blogs')
                else:
                    new_tags.append('ADMIN SIDE - Blogs')

            # 9. Faculty & Mentors
            elif path.startswith('/api/v1/faculty') or path.startswith('/api/v1/faculties'):
                if method.lower() == 'get' and not path.endswith('/stats/'):
                    new_tags.append('USER SIDE - Faculty')
                    new_tags.append('ADMIN SIDE - Faculty')
                else:
                    new_tags.append('ADMIN SIDE - Faculty')

            # 10. Gallery Items
            elif path.startswith('/api/v1/gallery/'):
                if method.lower() == 'get' and not path.endswith('/stats/'):
                    new_tags.append('USER SIDE - Gallery')
                    new_tags.append('ADMIN SIDE - Gallery')
                else:
                    new_tags.append('ADMIN SIDE - Gallery')

            # 11. Testimonials & Reviews
            elif path.startswith('/api/v1/testimonials/'):
                if method.lower() == 'get' and not path.endswith('/stats/'):
                    new_tags.append('USER SIDE - Testimonials')
                    new_tags.append('ADMIN SIDE - Testimonials')
                else:
                    new_tags.append('ADMIN SIDE - Testimonials')

            # Fallback
            else:
                tag_str = " ".join(current_tags).lower()
                if 'admin' in tag_str:
                    new_tags.append(f"ADMIN SIDE - {current_tags[0]}")
                elif 'student' in tag_str or 'user' in tag_str:
                    new_tags.append(f"USER SIDE - {current_tags[0]}")
                else:
                    new_tags.append(f"USER SIDE - {current_tags[0] if current_tags else 'General'}")

            operation['tags'] = new_tags

    # Clean curated tag ordering: USER SIDE tags first, followed by ADMIN SIDE tags
    user_order = [
        ('USER SIDE - Authentication', 'Student signup, login, password recovery & token verification'),
        ('USER SIDE - Student Portal & Profile', 'Student self-service portal, bio & personal details'),
        ('USER SIDE - Student Opted Courses', 'Course enrollments and opted course details for students'),
        ('USER SIDE - Student Resource Purchases', 'Digital learning resources, materials and purchases'),
        ('USER SIDE - Student Invoices & Payments', 'Student invoices, tax receipts and payment verification'),
        ('USER SIDE - Student Documents', 'Student document uploads, certificates and verification files'),
        ('USER SIDE - Courses', 'Public course catalog, syllabus, level and categories'),
        ('USER SIDE - Resources', 'Public catalog of available career and guidance study materials'),
        ('USER SIDE - Blogs', 'Public news, insights, blog articles and educational topics'),
        ('USER SIDE - Faculty', 'Public faculty directory, qualifications, bio and credentials'),
        ('USER SIDE - Testimonials', 'Public student reviews, feedback and success testimonials'),
        ('USER SIDE - Gallery', 'Public photo gallery albums, categories and event pictures'),
        ('USER SIDE - Enquiries & Contact', 'Public enquiry forms, contact submissions and lead generation'),
        ('USER SIDE - Portal Settings', 'Public portal branding, contact details, social links and metadata'),
    ]

    admin_order = [
        ('ADMIN SIDE - Dashboard', 'Executive overview metrics, student counts, financial summaries'),
        ('ADMIN SIDE - Authentication', 'Administrator and staff login, OTP authentication & password changes'),
        ('ADMIN SIDE - Admin Profile', 'Administrator profile management and security settings'),
        ('ADMIN SIDE - Students & Enrolments', 'Student candidate directory, enrolment register, stats & tax invoices'),
        ('ADMIN SIDE - Courses', 'Course lifecycle management, curriculum, pricing, faculty assignments & categories'),
        ('ADMIN SIDE - Resources', 'Study materials management, PDF uploads, pricing and categories'),
        ('ADMIN SIDE - Blogs', 'Blog post authoring, publishing workflow, stats and category management'),
        ('ADMIN SIDE - Faculty', 'Faculty roster management, achievements, bios and assignments'),
        ('ADMIN SIDE - Testimonials', 'Student testimonial moderation, publishing toggles and analytics'),
        ('ADMIN SIDE - Gallery', 'Gallery media uploads, category organization and media storage'),
        ('ADMIN SIDE - Enquiries & Leads', 'Inbound leads, admissions CRM, status tracking, email replies & CSV export'),
        ('ADMIN SIDE - Portal Settings', 'Platform-wide configurations, branding, contact info and feature flags'),
    ]

    all_used_tags = set()
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if isinstance(operation, dict):
                for t in operation.get('tags', []):
                    all_used_tags.add(t)

    sorted_tags = []
    for tag_name, tag_desc in user_order:
        if tag_name in all_used_tags:
            sorted_tags.append({'name': tag_name, 'description': tag_desc})
    for t in sorted(all_used_tags):
        if t.startswith('USER SIDE') and not any(x['name'] == t for x in sorted_tags):
            sorted_tags.append({'name': t, 'description': f'Endpoints belonging to {t}'})

    for tag_name, tag_desc in admin_order:
        if tag_name in all_used_tags:
            sorted_tags.append({'name': tag_name, 'description': tag_desc})
    for t in sorted(all_used_tags):
        if t.startswith('ADMIN SIDE') and not any(x['name'] == t for x in sorted_tags):
            sorted_tags.append({'name': t, 'description': f'Endpoints belonging to {t}'})

    for t in sorted(all_used_tags):
        if not t.startswith('USER SIDE') and not t.startswith('ADMIN SIDE'):
            sorted_tags.append({'name': t, 'description': f'Endpoints belonging to {t}'})

    result['tags'] = sorted_tags

    # Also sort paths dictionary so endpoints with USER SIDE operations come first
    def path_sort_key(item):
        path_str, methods_dict = item
        # If any operation has USER SIDE tag, prioritize it
        has_user = any(
            any(t.startswith('USER SIDE') for t in op.get('tags', []))
            for op in methods_dict.values() if isinstance(op, dict)
        )
        return (0 if has_user else 1, path_str)

    result['paths'] = dict(sorted(paths.items(), key=path_sort_key))

    return result
