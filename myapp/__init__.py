from os.path import dirname, join, realpath

from flask import Flask
from .extension import api
from .admin.routes import admin
from .designers.routes import designers
from .extension import db
from .extension import jwt
import datetime

from .extension import mail
from .extension import executor

app = Flask(__name__)

pymysql_connect_kwargs = {'user': 'root',
                          'password': '',
                          'host': '127.0.0.1',
                          'database': 'graphics'}

app.config['pymysql_kwargs'] = pymysql_connect_kwargs
UPLOAD_FOLDER = join(dirname(realpath(__file__)), 'static/uploads/')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

app.config['MAIL_SERVER'] = 'mail.howtoinkenya.co.ke'
app.config["MAIL_PORT"] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config["MAIL_USERNAME"] = 'mamafua@howtoinkenya.co.ke'
app.config["MAIL_PASSWORD"] = 'paw7KuZ%hHzq'

mail.init_app(app)
jwt.init_app(app)
db.init_app(app)

secret = "ts-c5nmxNzyu7xfdq-GmQxBYb_muHe4p3G1w26UxtHM"
app.secret_key = secret

app.config['JWT_SECRET_KEY'] = secret  # Change this!
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(minutes=60)
app.config['JWT_COOKIE_CSRF_PROTECT'] = True
app.config['JWT_CSRF_CHECK_FORM'] = True
# app.config['BASE_URL'] = 'http://127.0.0.1:5000'
app.config['PROPAGATE_EXCEPTIONS'] = True

app.config['MAIL_SERVER']='mail.howtoinkenya.co.ke'
app.config["MAIL_PORT"] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config["MAIL_USERNAME"] = 'mamafua@howtoinkenya.co.ke'
app.config["MAIL_PASSWORD"] = 'paw7KuZ%hHzq'

app.config.from_mapping(
    EXECUTOR_TYPE='thread',
    EXECUTOR_MAX_WORKERS="5",
    EXECUTOR_PROPAGATE_EXCEPTIONS=True
)
executor.init_app(app)

app.register_blueprint(admin)
app.register_blueprint(designers)


if __name__ == '__main__':
    app.run()
