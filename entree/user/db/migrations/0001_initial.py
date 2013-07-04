# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'EntreeDBUser'
        db.create_table(u'db_entreedbuser', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('last_login', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('key', self.gf('django.db.models.fields.CharField')(unique=True, max_length=40, db_index=True)),
            ('username', self.gf('django.db.models.fields.CharField')(unique=True, max_length=60, db_index=True)),
            ('app_data', self.gf('app_data.fields.AppDataField')(default='{}')),
        ))
        db.send_create_signal(u'db', ['EntreeDBUser'])


    def backwards(self, orm):
        # Deleting model 'EntreeDBUser'
        db.delete_table(u'db_entreedbuser')


    models = {
        u'db.entreedbuser': {
            'Meta': {'object_name': 'EntreeDBUser'},
            'app_data': ('app_data.fields.AppDataField', [], {'default': "'{}'"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40', 'db_index': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '60', 'db_index': 'True'})
        }
    }

    complete_apps = ['db']