from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from .models import Student, Teacher, Product, CartItem, Order, ReturnRequest, Message, Group, Reaction
from .utils import generate_otp, send_otp_email
import random
from decimal import Decimal
import uuid
from django.utils import timezone
from django.http import JsonResponse
from .models import Student, Teacher, LostFoundItem, Claim
from .forms import LostFoundItemForm, ClaimForm
from django.utils import timezone

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.utils import timezone
import json
from .models import EventPin, SavedLocation
from .utils import load_floor_graph,multi_floor_route
from django.utils.timezone import now
import google.generativeai as genai




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

    # Build the server cart snapshot for the dropdown
    cart_items = []
    total_price = 0

    cart_id = request.session.get('cart_id')
    if cart_id:
        cart_items = (CartItem.objects
                      .filter(cart_id=cart_id)
                      .select_related('product'))
    elif request.user.is_authenticated:
        cart = cart.objects.filter(user=request.user).first()
        if cart:
            cart_items = (CartItem.objects
                          .filter(cart=cart)
                          .select_related('product'))

    total_price = sum(item.product.price * item.quantity for item in cart_items)

    return render(request, 'login/shop.html', {
        'products': products,
        'cart_items': cart_items,
        'total_price': total_price,
    })


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

def _get_user_objects_for_session(request):
    """
    Helper: returns (user_obj, filter_kwargs) based on session user_type/user_id.
    filter_kwargs can be used to ensure CartItem belongs to that user.
    """
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    if not user_id or not user_type:
        return None, {}

    if user_type == "student":
        try:
            user = Student.objects.get(id=user_id)
            return user, {"student": user, "teacher__isnull": True}
        except Student.DoesNotExist:
            return None, {}
    elif user_type == "teacher":
        try:
            user = Teacher.objects.get(id=user_id)
            return user, {"teacher": user, "student__isnull": True}
        except Teacher.DoesNotExist:
            return None, {}
    return None, {}

def _compute_cart_totals_for_user(filter_kwargs):
    """
    Helper: compute grand total and total items for current user.
    """
    items = CartItem.objects.filter(**filter_kwargs).select_related("product")
    grand = Decimal("0.00")
    count = 0
    for it in items:
        grand += (it.product.price * it.quantity)
        count += it.quantity
    return grand, count

def decrement_cart(request, cart_item_id):
    """
    Decrease a CartItem quantity by 1 for the logged-in user.
    If quantity reaches 0, delete the item.
    - If AJAX (X-Requested-With=XMLHttpRequest), return JSON with fresh totals.
    - Otherwise, redirect back to the main cart page.
    """
    user, filter_kwargs = _get_user_objects_for_session(request)
    if not user:
        # Not logged in → send to login for non-AJAX; JSON for AJAX
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "error": "not_authenticated"}, status=401)
        return redirect("login")

    # Ensure the cart item belongs to this user
    try:
        item = CartItem.objects.select_related("product").get(id=cart_item_id, **filter_kwargs)
    except CartItem.DoesNotExist:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "error": "not_found"}, status=404)
        return redirect("cart")

    # Decrement or delete
    deleted = False
    if item.quantity > 1:
        item.quantity -= 1
        item.save()
    else:
        item.delete()
        deleted = True

    # Compute latest totals
    grand_total, total_items = _compute_cart_totals_for_user(filter_kwargs)

    # If AJAX, return details (including this row's new total if not deleted)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        data = {
            "ok": True,
            "deleted": deleted,
            "item_id": cart_item_id,
            "grand_total": f"{grand_total:.2f}",
            "cart_count": total_items,
        }
        if not deleted:
            row_total = item.product.price * item.quantity
            data["quantity"] = item.quantity
            data["row_total"] = f"{row_total:.2f}"
            data["price"] = f"{item.product.price:.2f}"
        return JsonResponse(data)

    # Non-AJAX → just go back to main cart
    return redirect("cart")

def increment_cart(request, product_id):
    """
    Increase quantity of the product in the current user's cart by 1.
    - If no cart item exists, create one with quantity=1.
    - If AJAX (XMLHttpRequest), return JSON with updated qty/row_total/grand_total/cart_count.
    - Otherwise, redirect back to 'cart'.
    """
    user, filter_kwargs = _get_user_objects_for_session(request)
    if not user:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "error": "not_authenticated"}, status=401)
        return redirect("login")

    # Find or create the cart item for this product
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "error": "product_not_found"}, status=404)
        return redirect("cart")

    # Determine owner fields
    ci_kwargs = {"product": product}
    if "student" in filter_kwargs:
        ci_kwargs["student"] = filter_kwargs["student"]
    if "teacher" in filter_kwargs:
        ci_kwargs["teacher"] = filter_kwargs["teacher"]

    item, created = CartItem.objects.select_related("product").get_or_create(**ci_kwargs, defaults={"quantity": 0})
    item.quantity = (item.quantity or 0) + 1
    item.save()

    grand_total, total_items = _compute_cart_totals_for_user(filter_kwargs)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        row_total = item.product.price * item.quantity
        return JsonResponse({
            "ok": True,
            "created": created,
            "item_id": item.id,
            "product_id": product_id,
            "quantity": item.quantity,
            "price": f"{item.product.price:.2f}",
            "row_total": f"{row_total:.2f}",
            "grand_total": f"{grand_total:.2f}",
            "cart_count": total_items,
        })

    return redirect("cart")

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

def campus_map(request):
    if not request.session.get('user_id'):
        return redirect("login")
    return render(request, "login/cmapusmap.html")

def _current_user(request):
    """Return (user_obj, user_type) based on your session scheme."""
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type")  # "student" or "teacher"
    if not user_id:
        return None, None
    try:
        if user_type == "student":
            return Student.objects.get(id=user_id), "student"
        elif user_type == "teacher":
            t = Teacher.objects.get(id=user_id)
            if not t.is_approved:
                return None, None
            return t, "teacher"
    except (Student.DoesNotExist, Teacher.DoesNotExist):
        return None, None
    return None, None

def lost_found(request):
    """Main page: List LOST and FOUND items; map shows FOUND (with coords)."""
    # Lists
    lost_items = LostFoundItem.objects.filter(status="LOST").order_by("-created_at")
    found_items = LostFoundItem.objects.filter(status="FOUND").order_by("-found_at", "-created_at")

    # For the map: only items with coordinates
    found_with_coords = found_items.exclude(found_lat__isnull=True).exclude(found_lng__isnull=True)

    # Empty forms (modal usage)
    report_form = LostFoundItemForm()
    claim_form = ClaimForm()

    # We’ll pass coordinates for Leaflet
    markers = [
        {
            "id": it.id,
            "title": it.title,
            "lat": it.found_lat,
            "lng": it.found_lng,
            "snippet": (it.description[:120] + "…") if it.description and len(it.description) > 120 else (it.description or ""),
        }
        for it in found_with_coords
    ]

    return render(request, "login/lost_found.html", {
        "lost_items": lost_items,
        "found_items": found_items,
        "report_form": report_form,
        "claim_form": claim_form,
        "markers": markers,
    })

def report_item(request):
    """Create a new Lost/Found entry."""
    user, user_type = _current_user(request)
    if not user:
        messages.error(request, "Please log in to report an item.")
        return redirect("login")

    if request.method == "POST":
        form = LostFoundItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            if user_type == "student":
                item.reporter_student = user
            else:
                item.reporter_teacher = user
            # If status is FOUND and found_at not set, default to now
            if item.status == "FOUND" and not item.found_at:
                item.found_at = timezone.now()
            item.save()
            messages.success(request, "Item submitted!")
        else:
            messages.error(request, "Please fix the errors in the form.")
    return redirect("lost_found")

def submit_claim(request, item_id):
    """Submit a claim against an item with an answer to the question."""
    user, user_type = _current_user(request)
    if not user:
        messages.error(request, "Please log in to claim an item.")
        return redirect("login")

    item = get_object_or_404(LostFoundItem, pk=item_id)

    if request.method == "POST":
        form = ClaimForm(request.POST)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.item = item
            if user_type == "student":
                claim.claimant_student = user
            else:
                claim.claimant_teacher = user

            # Optional auto-approve if an exact correct_answer was provided
            if item.correct_answer and item.correct_answer.strip():
                if item.correct_answer.strip().lower() == claim.answer_text.strip().lower():
                    claim.status = "APPROVED"
                    claim.reviewed_at = timezone.now()
                    item.status = "CLAIMED"
                    item.save(update_fields=["status"])
                    messages.success(request, "Claim approved automatically. Item marked as CLAIMED.")
            claim.save()
            if claim.status == "PENDING":
                messages.success(request, "Claim submitted! The team will review it shortly.")
        else:
            messages.error(request, "Please provide a valid answer.")
    return redirect("lost_found")

def campus_map(request):
    user_type = request.session.get('user_type', 'student')
    creator_id = request.session.get('user_id')
    saved = []
    if creator_id:
        saved = list(SavedLocation.objects.filter(creator_type=user_type, creator_id=creator_id)
                     .values('id','name','floor','x','y'))
    return render(request, 'login/cmapusmap.html', {'saved_locations': saved})

def api_graph(request, floor: int):
    try:
        graph = load_floor_graph(floor)
        return JsonResponse({"ok": True, "graph": graph})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def api_route(request):
    """
    Multi-floor A* route finder.
    POST JSON:
    {
      "start": {"x":..,"y":..,"floor":..},
      "goal": {"x":..,"y":..,"floor":..}
    }
    """
    try:
        body = json.loads(request.body.decode("utf-8"))
        s, g = body["start"], body["goal"]
        result = multi_floor_route(s["floor"], s, g["floor"], g)
        return JsonResponse(result, status=200 if result["ok"] else 400)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def api_save_my_location(request):
    try:
        body = json.loads(request.body.decode('utf-8'))
        request.session['my_location'] = body
        request.session.modified = True
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)


from django.shortcuts import render, redirect
from django.contrib import messages
from .models import EventPin
from datetime import datetime

def events(request):
    """Render Events & Personal Pins page with full event details."""
    user_type = request.session.get("user_type", "student")
    creator_id = request.session.get("user_id")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        desc = request.POST.get("description", "").strip()
        floor = int(request.POST.get("floor", 1))
        x = float(request.POST.get("x"))
        y = float(request.POST.get("y"))
        is_public = "is_public" in request.POST
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")

        # Parse datetimes safely
        st = datetime.fromisoformat(start_time) if start_time else None
        et = datetime.fromisoformat(end_time) if end_time else None

        EventPin.objects.create(
            title=title,
            description=desc,
            floor=floor,
            x=x,
            y=y,
            start_time=st,
            end_time=et,
            is_public=is_public,
            creator_type=user_type,
            creator_id=creator_id,
        )
        messages.success(request, "Event saved successfully!")
        return redirect("events")

    # ✅ Show all pins you created (public + private)
    my_pins = list(
        EventPin.objects.filter(
            creator_type=user_type, creator_id=creator_id
        ).values("id", "title", "description", "floor", "x", "y", "start_time", "end_time", "is_public")
    )

    # ✅ Show all public events (including your own)
    public_pins = list(
        EventPin.objects.filter(is_public=True).values(
            "id", "title", "description", "floor", "x", "y", "start_time", "end_time", "is_public"
        )
    )

    # ✅ Clean up data for frontend
    for p in my_pins + public_pins:
        p["description"] = p.get("description") or ""
        if p.get("start_time"):
            p["start_time"] = str(p["start_time"])
        if p.get("end_time"):
            p["end_time"] = str(p["end_time"])

    return render(
        request,
        "login/events.html",
        {"my_pins": my_pins, "public_pins": public_pins},
    )


@require_http_methods(["POST"])
def delete_pin(request, pin_id):
    """Delete a pin belonging to the current user."""
    user_type = request.session.get("user_type", "student")
    creator_id = request.session.get("user_id")
    try:
        pin = EventPin.objects.get(
            id=pin_id, creator_type=user_type, creator_id=creator_id
        )
        pin.delete()
        messages.success(request, "Pin deleted successfully.")
    except EventPin.DoesNotExist:
        messages.error(request, "Pin not found or unauthorized.")
    return redirect("events")


# -----------------------------
# APIs (to stop import errors)
# -----------------------------
@csrf_exempt
def api_save_location(request):
    """Legacy API – allows JS to save a location name for a user."""
    try:
        data = json.loads(request.body.decode("utf-8"))
        SavedLocation.objects.create(
            name=data.get("name"),
            floor=int(data.get("floor")),
            x=float(data.get("x")),
            y=float(data.get("y")),
            creator_type=request.session.get("user_type", "student"),
            creator_id=request.session.get("user_id"),
        )
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)})


def api_my_saved_locations(request):
    """Return all saved locations for the current user (legacy support)."""
    user_type = request.session.get("user_type", "student")
    creator_id = request.session.get("user_id")
    data = list(
        SavedLocation.objects.filter(
            creator_type=user_type, creator_id=creator_id
        ).values("id", "name", "floor", "x", "y")
    )
    return JsonResponse({"ok": True, "locations": data})
GEMINI_MODEL_NAME = "gemini-1.5-flash-latest"

def _ensure_history(session):
    """Ensure a chat history exists in the session."""
    if "chat_history" not in session:
        # Gemini expects 'contents' as a list of {role, parts:[{text:...}]}
        session["chat_history"] = []
    return session["chat_history"]

def chatbot_page(request):
    """Simple page with a chat UI."""
    return render(request, "login/chatbot.html")  # or wherever your template lives

@csrf_exempt
def gemini_chat_api(request):
    """
    POST { "message": "your text" }
    -> { "reply": "model text", "usage": {...}, "timestamp": "..." }
    Keeps a short rolling history in session.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    
    try:
        payload = json.loads(request.body.decode("utf-8"))
        user_msg = (payload.get("message") or "").strip()
        if not user_msg:
            return JsonResponse({"error": "Empty message"}, status=400)

        # Get & update session history
        history = _ensure_history(request.session)

        # Append user message to history
        history.append({"role": "user", "parts": [{"text": user_msg}]})

        # Build the model and send the conversation (history + new msg)
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)

        # You can do "chat" for a stateful object, but here we inline the history for simplicity:
        response = model.generate_content(
            contents=history,
            generation_config={
                "temperature": 0.4,
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 1024,
            },
            safety_settings=[
                # (optional) keep defaults or add your own safety tuning
            ],
        )

        # Extract the text
        reply_text = ""
        if response and response.candidates:
            parts = response.candidates[0].content.parts
            reply_text = "".join(getattr(p, "text", "") for p in parts if getattr(p, "text", None))

        if not reply_text:
            reply_text = "Sorry, I couldn't generate a response."

        # Append assistant reply to history
        history.append({"role": "model", "parts": [{"text": reply_text}]})

        # Keep only the last N turns to keep request payload small
        MAX_TURNS = 12  # user+assistant pairs ≈ 24 messages
        if len(history) > MAX_TURNS * 2:
            request.session["chat_history"] = history[-MAX_TURNS * 2 :]
        else:
            request.session["chat_history"] = history

        request.session.modified = True

        # (Optional) include very light usage info if present
        usage = {}
        try:
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                um = response.usage_metadata
                usage = {
                    "prompt_token_count": getattr(um, "prompt_token_count", None),
                    "candidates_token_count": getattr(um, "candidates_token_count", None),
                    "total_token_count": getattr(um, "total_token_count", None),
                }
        except Exception:
            pass

        return JsonResponse(
            {"reply": reply_text, "usage": usage, "timestamp": now().isoformat()},
            status=200,
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        # Log as needed
        return JsonResponse({"error": str(e)}, status=500)
    
