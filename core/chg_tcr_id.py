import os
import django

if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "embapp.settings")
    django.setup()

    import pandas as pd
    # pylint: disable=import-error
    from core.models import Tcr
    import psycopg2
    import sqlalchemy
    from sqlalchemy import create_engine

    obj = Tcr.objects.all()[0]
    print(obj)