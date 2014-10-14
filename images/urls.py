from django.conf.urls import patterns, url
from images import views

urlpatterns = patterns('',
	url(r'^$', views.index, name='index'),
	url(r'^new/$', views.new, name='new'),
	url(r'^create/$', views.create, name='create'),
	url(r'^edit/$', views.edit, name='edit'),
	url(r'^error/$', views.error, name='error'),
)