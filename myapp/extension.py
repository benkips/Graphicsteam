from flask_restful import  Api
from flask_pymysql import MySQL
from flask_mail import Mail
from flask_executor import Executor
from flask_session import Session
from flask_jwt_extended import JWTManager

api = Api()
db=MySQL()
mail = Mail()
executor = Executor()
sess=Session()
jwt = JWTManager()