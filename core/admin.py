from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Bed, Booking, PG, Review, Room, User


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
	list_display = ('username', 'email', 'user_type', 'gender', 'age', 'is_staff')
	list_filter = BaseUserAdmin.list_filter + ('user_type', 'gender')
	fieldsets = BaseUserAdmin.fieldsets + (
		('Additional Information', {'fields': ('user_type', 'age', 'occupation', 'gender', 'contact_number')}),
	)
	add_fieldsets = BaseUserAdmin.add_fieldsets + (
		(
			'Additional Information',
			{
				'classes': ('wide',),
				'fields': ('user_type', 'age', 'occupation', 'gender', 'contact_number'),
			},
		),
	)


@admin.register(PG)
class PGAdmin(admin.ModelAdmin):
	list_display = ('pg_name', 'owner', 'pg_type', 'area')
	list_filter = ('pg_type', 'area')
	search_fields = ('pg_name', 'area', 'owner__username', 'owner__email')


admin.site.register(Room)
admin.site.register(Bed)
admin.site.register(Booking)
admin.site.register(Review)
