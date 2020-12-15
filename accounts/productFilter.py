import django_filters
from django_filters import DateFilter, CharFilter

from .models import *

class ProductFilter(django_filters.FilterSet):
	start_date = DateFilter(field_name="date_created", lookup_expr='gte')
	end_date = DateFilter(field_name="date_created", lookup_expr='lte')
	description = CharFilter(field_name='description', lookup_expr='icontains')


	class Meta:
		model = Product
		fields = ['name', 'date_created','price','category','description']
		# exclude = ['name', 'date_created','price','category','description']


