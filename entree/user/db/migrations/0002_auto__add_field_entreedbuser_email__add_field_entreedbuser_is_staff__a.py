# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'EntreeDBUser.email'
        db.add_column(u'db_entreedbuser', 'email',
                      self.gf('django.db.models.fields.EmailField')(default='', max_length=75, blank=True),
                      keep_default=False)

        # Adding field 'EntreeDBUser.is_staff'
        db.add_column(u'db_entreedbuser', 'is_staff',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'EntreeDBUser.is_superuser'
        db.add_column(u'db_entreedbuser', 'is_superuser',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'EntreeDBUser.is_active'
        db.add_column(u'db_entreedbuser', 'is_active',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)

        # Adding field 'EntreeDBUser.date_joined'
        db.add_column(u'db_entreedbuser', 'date_joined',
                      self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'EntreeDBUser.email'
        db.delete_column(u'db_entreedbuser', 'email')

        # Deleting field 'EntreeDBUser.is_staff'
        db.delete_column(u'db_entreedbuser', 'is_staff')

        # Deleting field 'EntreeDBUser.is_superuser'
        db.delete_column(u'db_entreedbuser', 'is_superuser')

        # Deleting field 'EntreeDBUser.is_active'
        db.delete_column(u'db_entreedbuser', 'is_active')

        # Deleting field 'EntreeDBUser.date_joined'
        db.delete_column(u'db_entreedbuser', 'date_joined')


    models = {
        u'db.entreedbuser': {
            'Meta': {'object_name': 'EntreeDBUser'},
            'app_data': ('app_data.fields.AppDataField', [], {'default': "'{}'"}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40', 'db_index': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '60', 'db_index': 'True'})
        }
    }

    complete_apps = ['db']