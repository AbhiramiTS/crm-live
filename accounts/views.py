from django.shortcuts import render, redirect 
from django.http import HttpResponse
from django.forms import inlineformset_factory
from django.contrib.auth.models import User

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
# Create your views here.
from .models import *
from .forms import OrderForm, CreateUserForm
from .productForms import ProductForm
from .customerForms import CustomerForm
from .filters import OrderFilter
from .productFilter import ProductFilter
import datetime
from datetime import date, timedelta

from .decorators import unauthenticated_user, allowed_users, admin_only

from django.views.decorators.csrf import csrf_protect

@unauthenticated_user
def registerPage(request):
	form = CreateUserForm()
	if request.method == 'POST':
		form = CreateUserForm(request.POST)
		if form.is_valid():
			user = form.save()
			username = form.cleaned_data.get('username')


			messages.success(request, 'Account was created for ' + username)

			return redirect('login')
		

	context = {'form':form}
	return render(request, 'accounts/register.html', context)
	
@csrf_protect
@unauthenticated_user
def loginPage(request):
	if request.method == 'POST':
		username = request.POST.get('username')
		password =request.POST.get('password')

		user = authenticate(request, username=username, password=password)

		if user is not None:
			login(request, user)
			return redirect('home')
		else:
			messages.info(request, 'Username OR password is incorrect')

	context = {}
	return render(request, 'accounts/login.html', context)

@csrf_protect
def logoutUser(request):
	logout(request)
	return redirect('login')



@login_required(login_url='login')
@allowed_users(allowed_roles=['customer'])
def userPage(request):
	orders = request.user.customer.order_set.all()
	total_orders = orders.count()
	delivered = orders.filter(status='Delivered').count()
	pending = orders.filter(status='Pending').count()
	customer_id =  request.user.customer.id
	print('ORDERS:', orders)


	for order in orders:
		if order.quantity >= 0:
			order.order_price = order.product.price * order.quantity
			order.save()

	context = {'orders':orders, 'total_orders':total_orders,
	'delivered':delivered,'pending':pending, 'customer_id':customer_id}
	return render(request, 'accounts/user.html', context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['customer'])
def accountSettings(request):
	customer = request.user.customer
	
	form = CustomerForm(instance=customer)

	if request.method == 'POST':
		form = CustomerForm(request.POST, request.FILES,instance=customer)
		if form.is_valid():
			form.save()


	context = {'form':form, 'customer':customer}
	return render(request, 'accounts/account_settings.html', context)


@login_required(login_url='login')
@admin_only
def home(request):
	orders = Order.objects.all()
	customers = Customer.objects.all()

	
	this_week =date.today()-timedelta(days=7)
	this_week_orders = Order.objects.filter(date_created__gte=this_week)

	last_week=date.today()-timedelta(days=14)
	last_week_orders = Order.objects.filter(date_created__gte=last_week).filter(date_created__lte=this_week)

	previous_week=date.today()-timedelta(days=21)
	previous_week_orders = Order.objects.filter(date_created__gte=previous_week).filter(date_created__lte=last_week)
	

		# The products Out of Stock
	products_count= Product.objects.filter(inStock__lte = 1)
	product_count = products_count.count()

	total_customers = customers.count()

	total_orders = orders.count()
	delivered = orders.filter(status='Delivered').count()
	pending = orders.filter(status='Pending').count()

	# To display the last 10 orders
	order_items = Order.objects.all().order_by('id').reverse()

	context = {'orders':orders, 'customers':customers,
	'total_orders':total_orders,'delivered':delivered,
	'pending':pending, 'order_items':order_items, 'product_count':product_count,
	'this_week_orders':this_week_orders,'last_week_orders':last_week_orders,'previous_week_orders':previous_week_orders}

	return render(request, 'accounts/dashboard.html', context)

# CUSTOMERS
@login_required(login_url='login')
def customer(request, pk_test):
	customer = Customer.objects.get(id=pk_test)

	orders = customer.order_set.all()
	price = 0
	for order in orders:
		price = price + order.product.price
	order_count = orders.count()

	for order in orders:
		if order.quantity >= 0:
			order.order_price = order.product.price * order.quantity
			order.save()


	myFilter = OrderFilter(request.GET, queryset=orders)
	orders = myFilter.qs 

	context = {'customer':customer, 'orders':orders, 'order_count':order_count, 'total_price':price, 'myFilter':myFilter}
	return render(request, 'accounts/customer.html',context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def allCustomers(request):
	customers = Customer.objects.all()
	context = {'customers':customers}
	return render(request, 'accounts/all_customers.html',context)


@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def updateCustomer(request, pk):

	customer = Customer.objects.get(id=pk)
	form = CustomerForm(instance=customer)

	if request.method == 'POST':
		form = CustomerForm(request.POST, instance=customer)
		if form.is_valid():
			form.save()
			return redirect('/customer/'+pk)

	context = {'form':form,'customer_id':pk}
	return render(request, 'accounts/customer_form.html', context)



#ORDERS
@login_required(login_url='login')
@allowed_users(allowed_roles=['admin','customer'])
def createOrder(request, pk):
	OrderFormSet = inlineformset_factory(Customer, Order, fields=('product', 'status','quantity','note'), extra=10)
	customer = Customer.objects.get(id=pk)
	formset = OrderFormSet(queryset=Order.objects.none(),instance=customer)
	#form = OrderForm(initial={'customer':customer})
	if request.method == 'POST':
		#print('Printing POST:', request.POST)
		#form = OrderForm(request.POST)
		formset = OrderFormSet(request.POST, instance=customer)
	
		if formset.is_valid():
			# Automatically decrements the InStock Value when Status is 'DELIVERED'
			for fm in formset:
				val = fm.cleaned_data
				product_name = val['product']
				product_val = Product.objects.get(product_id=product_name.product_id)
				# If No Stock left, return back to home page
				if product_val.inStock < 1:
						message = {'message':'Product Out of Stock. Please Contact the Admin'}
						return render(request, 'accounts/message.html', message)

				if val['status'] == 'Delivered':
					product_val.inStock -= 1
					product_val.save()
					
			formset.save()
			return redirect('/')

	context = {'form':formset,'customer_id':pk}
	return render(request, 'accounts/order_form.html', context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def updateOrder(request, pk):

	order = Order.objects.get(id=pk)
	form = OrderForm(instance=order)

	customer_id = order.customer.id

	if request.method == 'POST':
		form = OrderForm(request.POST, instance=order)
		if form.is_valid():
			form.save()
			return redirect('/')

	context = {'form':form,'customer_id':customer_id}
	return render(request, 'accounts/order_form.html', context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def deleteOrder(request, pk):
	order = Order.objects.get(id=pk)
	if request.method == "POST":
		order.delete()
		return redirect('/')

	context = {'item':order}
	return render(request, 'accounts/delete.html', context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def deleteAllOrders(request,pk):

	if request.method == "POST":
		customer = Customer.objects.get(id=pk)
		orders = customer.order_set.all()
		orders.delete()
		return redirect('/')
	context = {'item':pk}
	return render(request, 'accounts/delete_all_orders.html',context)


#PRODUCTS
@login_required(login_url='login')
def products(request):
	products = Product.objects.all()
	count = products.count()

	myFilter = ProductFilter(request.GET, queryset=products)
	products = myFilter.qs 


	context = {'products':products, 'count':count,  'myFilter':myFilter}
	return render(request, 'accounts/products.html', context )

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def updateProduct(request, pk):

	product = Product.objects.get(product_id=pk)
	form = ProductForm(instance=product)

	if request.method == 'POST':
		form = ProductForm(request.POST, instance=product)
		if form.is_valid():
			form.save()
			return redirect('/products/')

	context = {'form':form}
	return render(request, 'accounts/product_form.html', context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def deleteProduct(request, pk):
	product = Product.objects.get(product_id=pk)
	if request.method == "POST":
		product.delete()
		return redirect('/products/')

	context = {'item':product}
	return render(request, 'accounts/delete_products.html', context)

@login_required(login_url='login')
@allowed_users(allowed_roles=['admin'])
def createProduct(request):
	product = Product.objects.all()
	form = ProductForm()
	if request.method == 'POST':
		#print('Printing POST:', request.POST)
		form = ProductForm(request.POST)

		if form.is_valid():
			form.save()
			return redirect('/')

	context = {'form':form}
	return render(request, 'accounts/product_form.html', context)

@login_required(login_url='login')
def productStock(request):
	products = Product.objects.filter(inStock__lte = 1)
	count = products.count()
	
	myFilter = ProductFilter(request.GET, queryset=products)
	products = myFilter.qs 

	context = {'products':products, 'count':count,  'myFilter':myFilter, 'data':'Out of Stock'}
	return render(request, 'accounts/products.html', context)


# List the Orders
"""
	TODO: Instead of writing seperate functions for listing orders, 
	create a function and perform all 3 operations in that single function itself.

"""
@login_required(login_url='login')
def orderList(request):
	order = Order.objects.all()
	count = order.count()

	myFilter = OrderFilter(request.GET, queryset=order)
	order = myFilter.qs 

	price = 0
	for orders in order:
			price = price + orders.order_price
	

	context = {'order':order, 'count':count, 'orders':'Total Orders','price':price,'myFilter':myFilter}
	return render(request, 'accounts/all_orders.html', context )

@login_required(login_url='login')
def orderDelivered(request):
	order = Order.objects.filter(status='Delivered')
	count = order.count()

	price = 0
	for orders in order:
		price = price + orders.order_price

	myFilter = OrderFilter(request.GET, queryset=order)
	order = myFilter.qs 

	context = {'order':order, 'count':count, 'orders':'Orders Delivered','price':price,'myFilter':myFilter}
	return render(request, 'accounts/all_orders.html', context )

@login_required(login_url='login')
def orderPending(request):
	order = Order.objects.filter(status='Pending')
	count = order.count()

	myFilter = OrderFilter(request.GET, queryset=order)
	order = myFilter.qs 

	price = 0
	for orders in order:
		price = price + orders.order_price

	context = {'order':order, 'count':count, 'orders':'Pending','price':price,'myFilter':myFilter}
	return render(request, 'accounts/all_orders.html', context )

	
