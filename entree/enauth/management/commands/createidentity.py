"""
Management utility to create Entree identity
"""
import sys
import getpass

from optparse import make_option

from django.core.exceptions import ValidationError
from django.core.management.base import CommandError, BaseCommand
from django.core.validators import validate_email
from django.db.utils import DEFAULT_DB_ALIAS

from entree.enauth.models import Identity


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
            make_option('--email', dest='email', default=None,
                help='Specifies the email address for the identity.'),
            make_option('--noinput', action='store_false', dest='interactive', default=True,
                help=('Tells Django to NOT prompt the user for input of any kind. '
                      'You must use --username and --email with --noinput, and '
                      'superusers created with --noinput will not be able to log '
                      'in until they\'re given a valid password.')),
            make_option('--database', action='store', dest='database',
                default=DEFAULT_DB_ALIAS, help='Specifies the database to use. Default is "default".'),
        )

    help = 'Used to create an Entree identity.'

    def handle(self, *args, **options):
        email = options.get('email', None)
        interactive = options.get('interactive')
        verbosity = int(options.get('verbosity', 1))
        database = options.get('database')
        password = None

        try:
            if not interactive:
                if not email:
                    raise CommandError("You must provide --email with --noinput.")

                try:
                    validate_email(email)
                except ValidationError:
                    raise CommandError("Error: Given e-mail address is invalid.\n")

            else:
                while 1:
                    if not email:
                        email = raw_input('E-mail address: ')
                    try:
                        validate_email(email)
                    except ValidationError:
                        sys.stderr.write("Error: Given e-mail address is invalid.\n")
                        email = None
                    else:
                        break

                # Get a password
                while 1:
                    if not password:
                        password = getpass.getpass("Password")
                        password2 = getpass.getpass('Password (again): ')
                        if password != password2:
                            sys.stderr.write("Error: Your passwords didn't match.\n")
                            password = None
                            continue
                    if not password.strip():
                        sys.stderr.write("Error: Blank passwords aren't allowed.\n")
                        password = None
                        continue
                    break

        except KeyboardInterrupt:
            sys.stderr.write("\nOperation cancelled.\n")
            sys.exit(1)
        else:
            Identity.objects.db_manager(database).create(email=email, password=password)
            if verbosity:
              self.stdout.write("Identity created successfully.\n")
