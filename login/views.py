from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Q
from .models import Student, Teacher, Product, CartItem, Order, ReturnRequest, Message, Group, Reaction, Location,LostAndFound
from .utils import generate_otp, send_otp_email
import random
from decimal import Decimal
import uuid
from django.utils import timezone
from django.http import JsonResponse
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def register(request):
    if request.method == "POST":
        user_type = request.POST['user_type']
        name = request.POST['name']
        email = request.POST['email']
        id_number = request.POST['id_number']
        department = request.POST.get('department', '')
        phone = request.POST['phone_number']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("register")

        if Student.objects.filter(email=email).exists() or Teacher.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("register")

        if user_type == "student":
            if Student.objects.filter(student_id=id_number).exists():
                messages.error(request, "Student ID already registered")
                return redirect("register")
            user = Student(name=name, email=email, student_id=id_number, phone_number=phone)
            user.set_password(password)
            user.save()
            messages.success(request, "Registered successfully! Please login.")
            return redirect("login")
        elif user_type == "teacher":
            if Teacher.objects.filter(teacher_id=id_number).exists():
                messages.error(request, "Teacher ID already registered")
                return redirect("register")
            user = Teacher(name=name, email=email, teacher_id=id_number, department=department, phone_number=phone)
            user.set_password(password)
            user.save()
            messages.success(request, "Registration submitted! Await admin approval.")
            return redirect("login")

    return render(request, "login/register.html")

def login_request(request):
    if request.method == "POST":
        new_token = str(uuid.uuid4())
        request.session['login_attempt_token'] = new_token

        email = request.POST['email']
        password = request.POST['password']
        user_type = request.POST['user_type']

        try:
            if user_type == "student":
                user = Student.objects.get(email=email)
            elif user_type == "teacher":
                user = Teacher.objects.get(email=email)
                if not user.is_approved:
                    messages.error(request, "Your account is pending admin approval.")
                    return redirect("login")
            else:
                messages.error(request, "Invalid user type.")
                return redirect("login")

            if not user.check_password(password):
                messages.error(request, "Invalid password.")
                return redirect("login")

            request.session['user_id'] = user.id
            request.session['user_type'] = user_type
            request.session['email'] = email

            if not user.is_otp_verified:
                otp = generate_otp()
                request.session['otp'] = otp
                request.session['otp_expiry'] = (timezone.now() + timezone.timedelta(minutes=5)).timestamp()
                send_otp_email(email, otp)
                return redirect("verify_otp")
            messages.success(request, "Logged in successfully!")
            return redirect("dashboard")

        except (Student.DoesNotExist, Teacher.DoesNotExist):
            messages.error(request, "User does not exist.")
            return redirect("login")

    return render(request, "login/login.html")

def verify_otp(request):
    if request.method == "POST":
        otp = request.POST['otp']
        stored_otp = request.session.get('otp')
        otp_expiry = request.session.get('otp_expiry')

        if not stored_otp or not otp_expiry:
            messages.error(request, "No OTP session found. Please login again.")
            return redirect("login")

        if timezone.now().timestamp() > float(otp_expiry):
            messages.error(request, "OTP has expired. Please request a new one.")
            return redirect("login")

        if otp == stored_otp:
            user_type = request.session.get('user_type')
            email = request.session.get('email')
            try:
                if user_type == "student":
                    user = Student.objects.get(email=email)
                elif user_type == "teacher":
                    user = Teacher.objects.get(email=email)
                user.is_otp_verified = True
                user.save()
                messages.success(request, "OTP verified successfully!")
                return redirect("dashboard")
            except (Student.DoesNotExist, Teacher.DoesNotExist):
                messages.error(request, "User does not exist.")
                return redirect("login")
        else:
            messages.error(request, "Invalid OTP.")
            return redirect("verify_otp")

    return render(request, "login/verify_otp.html")

def dashboard(request):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    if not user_id:
        return redirect("login")
    try:
        if user_type == "student":
            user = Student.objects.get(id=user_id)
            orders = Order.objects.filter(student=user)
            context = {"user": user, "orders": orders, "user_type": user_type}
            

        elif user_type == "teacher":
            user = Teacher.objects.get(id=user_id)
            if not user.is_approved:
                messages.error(request, "Your account is pending admin approval.")
                return redirect("login")
            orders = Order.objects.filter(status='Pending')
            context = {"user": user, "orders": orders, "user_type": user_type}
        else:
            return redirect("login")
        return render(request, "login/student.html", context)
    except (Student.DoesNotExist, Teacher.DoesNotExist):
        return redirect("login")

def shop(request):
    products = Product.objects.all()
    return render(request, "login/shop.html", {"products": products})

def add_to_cart(request, product_id):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    if not user_id:
        return redirect("login")

    try:
        product = Product.objects.get(id=product_id)
        if user_type == "student":
            user = Student.objects.get(id=user_id)
            cart_item, created = CartItem.objects.get_or_create(student=user, product=product, defaults={'quantity': 1})
        elif user_type == "teacher":
            user = Teacher.objects.get(id=user_id)
            if not user.is_approved:
                messages.error(request, "Your account is pending admin approval.")
                return redirect("login")
            cart_item, created = CartItem.objects.get_or_create(teacher=user, product=product, defaults={'quantity': 1})
        else:
            return redirect("login")

        if not created:
            cart_item.quantity += 1
            cart_item.save()
        messages.success(request, "Product added to cart!")
        return redirect("shop")
    except (Product.DoesNotExist, Student.DoesNotExist, Teacher.DoesNotExist):
        messages.error(request, "Invalid product or user.")
        return redirect("shop")

def cart(request):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    if not user_id:
        return redirect("login")

    try:
        if user_type == "student":
            user = Student.objects.get(id=user_id)
            cart_items = CartItem.objects.filter(student=user)
        elif user_type == "teacher":
            user = Teacher.objects.get(id=user_id)
            if not user.is_approved:
                messages.error(request, "Your account is pending admin approval.")
                return redirect("login")
            cart_items = CartItem.objects.filter(teacher=user)
        else:
            return redirect("login")

        total_price = sum(item.product.price * item.quantity for item in cart_items)
        return render(request, "login/cart.html", {"cart_items": cart_items, "total_price": total_price})
    except (Student.DoesNotExist, Teacher.DoesNotExist):
        return redirect("login")

def remove_from_cart(request, cart_item_id):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    if not user_id:
        return redirect("login")

    try:
        if user_type == "student":
            cart_item = CartItem.objects.get(id=cart_item_id, student_id=user_id)
        elif user_type == "teacher":
            cart_item = CartItem.objects.get(id=cart_item_id, teacher_id=user_id)
        else:
            return redirect("login")
        cart_item.delete()
        messages.success(request, "Item removed from cart!")
        return redirect("cart")
    except CartItem.DoesNotExist:
        messages.error(request, "Item not found.")
        return redirect("cart")

def add_product(request):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    if not user_id or user_type != "teacher":
        messages.error(request, "Only approved teachers can add products.")
        return redirect("login")

    try:
        user = Teacher.objects.get(id=user_id)
        if not user.is_approved:
            messages.error(request, "Your account is pending admin approval.")
            return redirect("login")

        if request.method == "POST":
            name = request.POST['name']
            description = request.POST['description']
            price = request.POST['price']
            image = request.FILES.get('image')
            product = Product(name=name, description=description, price=price, image=image)
            product.save()
            messages.success(request, "Product added successfully!")
            return redirect("shop")
        return render(request, "login/add_product.html")
    except Teacher.DoesNotExist:
        return redirect("login")

def delete_product(request, product_id):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    if not user_id or user_type != "teacher":
        messages.error(request, "Only approved teachers can delete products.")
        return redirect("login")

    try:
        user = Teacher.objects.get(id=user_id)
        if not user.is_approved:
            messages.error(request, "Your account is pending admin approval.")
            return redirect("login")
        product = Product.objects.get(id=product_id)
        product.delete()
        messages.success(request, "Product deleted successfully!")
        return redirect("shop")
    except (Teacher.DoesNotExist, Product.DoesNotExist):
        messages.error(request, "Invalid product or user.")
        return redirect("shop")

def logout(request):
    request.session.flush()
    messages.success(request, "Logged out successfully!")
    return redirect("login")

def payment(request):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    if not user_id or user_type != "student":
        messages.error(request, "Only students can access payment.")
        return redirect("login")

    try:
        user = Student.objects.get(id=user_id)
        cart_items = CartItem.objects.filter(student=user)
        if not cart_items:
            messages.error(request, "Your cart is empty.")
            return redirect("cart")
        total_price = sum(item.product.price * item.quantity for item in cart_items)
        return render(request, "login/payment.html", {"total_amount": total_price})
    except Student.DoesNotExist:
        return redirect("login")

def process_payment(request):
    if request.method == "POST":
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        if not user_id or user_type != "student":
            messages.error(request, "Only students can process payments.")
            return redirect("login")

        try:
            user = Student.objects.get(id=user_id)
            cart_items = CartItem.objects.filter(student=user)
            if not cart_items:
                messages.error(request, "Your cart is empty.")
                return redirect("cart")
            total_price = sum(item.product.price * item.quantity for item in cart_items)
            payment_method = request.POST['payment_method']
            transaction_id = f"TXN{random.randint(100000, 999999)}"
            order = Order.objects.create(
                student=user,
                total_amount=total_price,
                payment_method=payment_method,
                transaction_id=transaction_id,
                status='Pending'
            )
            order.cart_items.set(cart_items)
            order.save()
            cart_items.delete()
            messages.success(request, "Payment submitted successfully!")
            return redirect("payment_success", order_id=order.id)
        except Student.DoesNotExist:
            messages.error(request, "User does not exist.")
            return redirect("login")
        except Exception as e:
            messages.error(request, f"Payment failed: {str(e)}")
            return redirect("payment_failure")
    return redirect("cart")

def payment_success(request, order_id):
    try:
        user_id = request.session.get('user_id')
        order = Order.objects.get(id=order_id, student_id=user_id)
        return render(request, "login/payment_success.html", {"order": order})
    except Order.DoesNotExist:
        messages.error(request, "Invalid order.")
        return redirect("dashboard")

def payment_failure(request):
    return render(request, "login/payment_failure.html")

def return_request(request):
    if request.method == "POST":
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        if not user_id or user_type != "student":
            messages.error(request, "Only students can request returns.")
            return redirect("login")

        order_id = request.POST.get('order_id')
        reason = request.POST.get('reason')

        try:
            order = Order.objects.get(id=order_id, student_id=user_id)
            ReturnRequest.objects.create(order=order, reason=reason)
            messages.success(request, "Return request submitted successfully!")
            return redirect("payment_success", order_id=order.id)
        except Order.DoesNotExist:
            messages.error(request, "Invalid order.")
            return redirect("payment")
    return redirect("payment_success")

def approve_orders(request):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    if not user_id or user_type != "teacher":
        messages.error(request, "Only approved teachers can approve orders.")
        return redirect("login")

    try:
        user = Teacher.objects.get(id=user_id)
        if not user.is_approved:
            messages.error(request, "Your account is pending admin approval.")
            return redirect("login")

        if request.method == "POST":
            order_ids = request.POST.getlist('order_ids')
            orders = Order.objects.filter(id__in=order_ids, status='Pending')
            updated_count = orders.update(status='Approved')
            messages.success(request, f"{updated_count} order(s) approved successfully!")
            return redirect("dashboard")
        return redirect("dashboard")
    except Teacher.DoesNotExist:
        return redirect("login")

def chat(request):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    
    if not user_id:
        messages.error(request, "Please log in to access messaging.")
        return redirect("login")
    
    try:
        if user_type == "student":
            current_user = Student.objects.get(id=user_id)
            users = Student.objects.exclude(id=user_id)
            groups = current_user.groups.all()
        elif user_type == "teacher":
            current_user = Teacher.objects.get(id=user_id)
            if not current_user.is_approved:
                messages.error(request, "Your account is pending admin approval.")
                return redirect("login")
            users = Student.objects.all()
            groups = current_user.groups.all()
        else:
            messages.error(request, "Invalid user type.")
            return redirect("login")
        
        selected_id = request.GET.get('id')
        selected_type = request.GET.get('type', 'user')
        messages_list = []
        selected = None
        
        if selected_id:
            if selected_type == 'user':
                try:
                    selected = Student.objects.get(id=selected_id)
                except Student.DoesNotExist:
                    messages.error(request, "Selected user does not exist.")
                    return redirect("chat")
                
                # Construct query based on user types
                query = Q(group=None)
                if user_type == "student":
                    query &= (
                        Q(sender=current_user, recipient=selected) |
                        Q(sender=selected, recipient=current_user)
                    )
                elif user_type == "teacher":
                    query &= (
                        Q(teacher_sender=current_user, recipient=selected)
                    )
                
                messages_list = Message.objects.filter(query).order_by('timestamp').prefetch_related('reactions')
            elif selected_type == 'group':
                try:
                    selected = Group.objects.get(id=selected_id)
                except Group.DoesNotExist:
                    messages.error(request, "Selected group does not exist.")
                    return redirect("chat")
                messages_list = Message.objects.filter(group=selected).order_by('timestamp').prefetch_related('reactions')
        
        return render(request, "login/chat.html", {
            "users": users,
            "groups": groups,
            "selected": selected,
            "selected_type": selected_type,
            "messages": messages_list,
            "user_id": user_id,
            "user_type": user_type,
        })
    
    except (Student.DoesNotExist, Teacher.DoesNotExist):
        messages.error(request, "Invalid user.")
        return redirect("login")

def create_group(request):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    if not user_id:
        messages.error(request, "Please log in to create a group.")
        return redirect("login")
    
    if request.method == "POST":
        name = request.POST['name']
        member_ids = request.POST.getlist('members')
        try:
            if user_type == "student":
                creator = Student.objects.get(id=user_id)
            else:
                creator = Teacher.objects.get(id=user_id)
                if not creator.is_approved:
                    messages.error(request, "Your account is pending admin approval.")
                    return redirect("login")
            
            group = Group.objects.create(name=name)
            if user_type == "student":
                group.members.add(creator)
            else:
                group.teacher_members.add(creator)
            for mid in member_ids:
                group.members.add(Student.objects.get(id=mid))
            messages.success(request, "Group created successfully!")
            return redirect("chat")
        except (Student.DoesNotExist, Teacher.DoesNotExist):
            messages.error(request, "Invalid user.")
            return redirect("create_group")
    
    users = Student.objects.all()
    return render(request, "login/create_group.html", {"users": users})

def send_message(request):
    if request.method == "POST":
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        
        if not user_id:
            messages.error(request, "Please log in to send messages.")
            return redirect("login")
        
        recipient_id = request.POST.get('recipient_id')
        group_id = request.POST.get('group_id')
        content = request.POST.get('content')
        file = request.FILES.get('file')
        voice = request.FILES.get('voice')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        try:
            if user_type == "student":
                sender = Student.objects.get(id=user_id)
                teacher_sender = None
            elif user_type == "teacher":
                sender = None
                teacher_sender = Teacher.objects.get(id=user_id)
                if not teacher_sender.is_approved:
                    messages.error(request, "Your account is pending admin approval.")
                    return redirect("login")
            else:
                messages.error(request, "Invalid user type.")
                return redirect("login")
            
            msg = Message.objects.create(
                sender=sender,
                teacher_sender=teacher_sender,
                content=content,
                file=file,
                voice=voice,
                latitude=latitude if latitude else None,
                longitude=longitude if longitude else None,
            )
            
            if group_id:
                group = Group.objects.get(id=group_id)
                msg.group = group
            elif recipient_id:
                recipient = Student.objects.get(id=recipient_id)
                msg.recipient = recipient
            else:
                messages.error(request, "Must specify recipient or group.")
                return redirect("chat")
            
            msg.save()
            
            response_data = {
                'status': 'success',
                'message': 'Message sent successfully!',
                'file': msg.file.url if msg.file else None,
                'voice': msg.voice.url if msg.voice else None,
            }
            return JsonResponse(response_data)
        
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return redirect("chat")

def add_reaction(request):
    if request.method == "POST":
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        if not user_id:
            messages.error(request, "Please log in to add reactions.")
            return redirect("login")
        
        message_id = request.POST.get('message_id')
        emoji = request.POST.get('emoji')
        
        try:
            if user_type == "student":
                user = Student.objects.get(id=user_id)
                teacher = None
            elif user_type == "teacher":
                user = None
                teacher = Teacher.objects.get(id=user_id)
                if not teacher.is_approved:
                    messages.error(request, "Your account is pending admin approval.")
                    return redirect("login")
            else:
                messages.error(request, "Invalid user type.")
                return redirect("login")
            
            message = Message.objects.get(id=message_id)
            reaction, created = Reaction.objects.get_or_create(
                message=message, user=user, teacher=teacher, emoji=emoji,
                defaults={'created_at': timezone.now()}
            )
            if not created:
                reaction.delete()
                messages.success(request, "Reaction removed!")
            else:
                messages.success(request, "Reaction added!")
            
            if message.group:
                return redirect(f"/chat/?id={message.group.id}&type=group")
            return redirect(f"/chat/?id={message.recipient.id}&type=user")
        
        except (Student.DoesNotExist, Teacher.DoesNotExist, Message.DoesNotExist):
            messages.error(request, "Invalid user or message.")
            return redirect("chat")
    
    return redirect("chat")

# login/views.py (relevant part)
def campus_map(request):
    if not request.session.get('user_id'):
        return redirect("login")
    
    # Fetch locations and group by floor
    locations = Location.objects.values('floor', 'name', 'latitude', 'longitude', 'description')
    markers_by_floor = {}
    for loc in locations:
        floor = loc['floor']
        if floor not in markers_by_floor:
            markers_by_floor[floor] = []
        markers_by_floor[floor].append({
            'lat': loc['latitude'],
            'lng': loc['longitude'],
            'title': loc['name'],
            'desc': loc['description']
        })
    
    return render(request, "login/campusmap.html", {
        'markers_by_floor': markers_by_floor
    })

def lost_and_found(request):
    if not request.session.get('user_id'):
        return redirect("login")
    
    user_id = request.session['user_id']
    user_type = request.session['user_type']
    
    item_type = request.GET.get('item_type', '')
    category = request.GET.get('category', '')
    items = LostAndFound.objects.all()
    if item_type:
        items = items.filter(item_type=item_type)
    if category:
        items = items.filter(category=category)
    
    if request.GET.get('format') == 'json':
        floor = request.GET.get('floor')
        if floor:
            items = items.filter(location__floor=floor)
        data = [
            {
                'id': item.id,
                'item_type': item.item_type,
                'description': item.description,
                'category_display': item.get_category_display(),
                'user_name': item.user.name if item.user else None,
                'teacher_name': item.teacher.name if item.teacher else None,
                'location': {
                    'latitude': item.location.latitude,
                    'longitude': item.location.longitude
                }
            } for item in items
        ]
        return JsonResponse(data, safe=False)
    
    return render(request, "login/lost.html", {
        'items': items,
        'item_types': LostAndFound.ITEM_TYPES,
        'categories': LostAndFound.CATEGORIES,
        'user_id': user_id,
        'user_type': user_type
    })

def add_lost_and_found(request):
    if not request.session.get('user_id'):
        return redirect("login")
    
    user_id = request.session['user_id']
    user_type = request.session['user_type']
    
    if request.method == "POST":
        item_type = request.POST.get('item_type')
        category = request.POST.get('category')
        description = request.POST.get('description')
        floor = request.POST.get('floor')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        # Validate inputs
        if not all([item_type, category, description, floor, latitude, longitude]):
            messages.error(request, "All fields are required, including a pinned location on the map.")
            return redirect("lost_and_found_map")
        
        try:
            floor = int(floor)
            latitude = float(latitude)
            longitude = float(longitude)
        except ValueError:
            messages.error(request, "Invalid location coordinates or floor number.")
            return redirect("lost_and_found_map")
        
        try:
            if user_type == "student":
                user = Student.objects.get(id=user_id)
                teacher = None
            elif user_type == "teacher":
                user = None
                teacher = Teacher.objects.get(id=user_id)
                if not teacher.is_approved:
                    messages.error(request, "Your account is pending admin approval.")
                    return redirect("lost_and_found")
            else:
                messages.error(request, "Invalid user type.")
                return redirect("lost_and_found")
            
            location = Location.objects.create(
                name=f"{item_type.capitalize()} Item Location",
                floor=floor,
                latitude=latitude,
                longitude=longitude,
                description=f"Location for {item_type} item: {description[:50]}"
            )
            
            item = LostAndFound.objects.create(
                user=user,
                teacher=teacher,
                item_type=item_type,
                category=category,
                description=description,
                location=location
            )
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "lost_and_found_group",
                {
                    "type": "chat_message",
                    "message": {
                        "action": "message",
                        "content": f"New {item_type} item: {description[:50]} at Floor {floor}",
                        "sender_id": user_id,
                        "sender_type": user_type,
                        "latitude": latitude,
                        "longitude": longitude
                    }
                }
            )
            
            messages.success(request, f"{item_type.capitalize()} item reported successfully!")
            return redirect("lost_and_found")
        
        except (Student.DoesNotExist, Teacher.DoesNotExist):
            messages.error(request, "Invalid user.")
            return redirect("lost_and_found")
    
    return redirect("lost_and_found_map")

def lost_and_found_map(request):
    if not request.session.get('user_id'):
        return redirect("login")
    
    user_id = request.session['user_id']
    user_type = request.session['user_type']
    
    item_type = request.GET.get('item_type', '')
    category = request.GET.get('category', '')
    items = LostAndFound.objects.all()
    if item_type:
        items = items.filter(item_type=item_type)
    if category:
        items = items.filter(category=category)
    
    return render(request, "login/lostmap.html", {
        'user_id': user_id,
        'user_type': user_type,
        'items': items,
        'item_types': LostAndFound.ITEM_TYPES,
        'categories': LostAndFound.CATEGORIES
    })