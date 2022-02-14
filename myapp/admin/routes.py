import urllib.parse
from functools import wraps
from io import BytesIO

import requests
import werkzeug
from flask_restful import reqparse, Resource
from werkzeug.security import safe_join

from myapp.extension import api, jwt
import datetime
import math
import os

import pymysql
from flask import Blueprint, render_template, make_response, request, jsonify, json, redirect, url_for, session, \
    current_app as app, send_from_directory
from werkzeug.utils import secure_filename
from myapp.extension import db
from flask_jwt_extended import (jwt_required, get_jwt_identity,
                                create_access_token, create_refresh_token,
                                set_access_cookies, set_refresh_cookies,
                                unset_jwt_cookies, unset_access_cookies, get_jwt)
from PIL import Image
from password_generator import PasswordGenerator
from flask import send_file
from flask_mail import Message
from myapp.extension import mail
import html
admin = Blueprint('admin', __name__, url_prefix="/admin/", template_folder='templates')
api.init_app(admin)

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])


# resize pic
def resizetool(fullpath):
    small = 540, 540

    ### small THUMBNAIL ###
    thumbnail_image = Image.open(fullpath)
    thumbnail_image.thumbnail(small, Image.LANCZOS)
    thumbnail_image.save(fullpath, optimize=True, quality=95)


# check if extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# delete file
def deleteany_file(filename):
    os.unlink(os.path.join(app.config['UPLOAD_FOLDER'], filename))


def sendmailstopple(contacts,uname, passw):
    with mail.connect() as conn:
        for email in contacts:
            message = f'Praise the LORD {uname}? \n Your username is : {uname} \n ' \
                      f'and password is : {passw}'
            subject = "Graphics Team Login Details"
            msg = Message(recipients=[email], sender=f'MediaFeeds<mediafeeds@ekarantechnologies.com>', \
                          body=message, subject=subject, reply_to='mediafeeds@ekarantechnologies.com')
            conn.send(msg)
            print(f'sent to {email}')


@jwt.unauthorized_loader
def unauthorized_callback(error):
    # No auth header
    if request.path.startswith('/admin/'):
        return make_response(redirect('/admin/', 302))
    else:
        return make_response(redirect('/designers/login', 302))


@jwt.invalid_token_loader
def invalid_token_callback():
    # Invalid Fresh/Non-Fresh Access token in auth header
    if request.path.startswith('/admin/'):
        resp = make_response(redirect('/admin/'))
    else:
        resp = make_response(redirect('/designers/login'))

    unset_jwt_cookies(resp)
    return resp, 302


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    # Expired auth header
    if request.path.startswith('/admin/'):
        resp = make_response(redirect('/admin/refreshingtokens'))
    else:
        resp = make_response(redirect('/designers/refreshtokens'))
    unset_access_cookies(resp)
    return resp


def assign_access_refresh_token(user_id, url):
    access_token = create_access_token(identity=str(user_id), fresh=True)
    refresh_token = create_refresh_token(identity=str(user_id))
    resp = make_response(redirect(url, 302))
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)
    return resp


def unset_jwt():
    resp = make_response(redirect('/admin/', 302))
    unset_jwt_cookies(resp)
    return resp


# login function
class Login(Resource):
    def get(self):
        return make_response(render_template("admin/login.html"))

    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('username', type=str, required=True, help='The username required', )
        post_parser.add_argument('password', type=str, required=True, help='The password required', )
        args = post_parser.parse_args()
        name = args['username']
        password = args['password']

        if (name and password):
            cur = db.connection.cursor(pymysql.cursors.DictCursor)
            sql = "SELECT * FROM members WHERE name = %s AND password = %s "
            val = (name, password)
            results = cur.execute(sql, val)
            if results > 0:
                data = cur.fetchall()
                cur.close()
                pid = data[0]['id']
                role = data[0]['role']
                status = data[0]['status']
                if status == 0:
                    error = 'Kindly visit the Designer account'
                    return assign_access_refresh_token(pid,
                                                       '/admin/Dashboard') if role == "admin" else make_response(
                        render_template('admin/login.html', error=error))
                else:
                    error = 'Account suspended,contact 254711114002'
                    return make_response(render_template('admin/login.html', error=error))



            else:
                cur.close()
                error = 'username and password could not match'
                return make_response(render_template('admin/login.html', error=error))

        else:
            error = 'Enter the required field'
            return make_response(render_template('admin/login.html', error=error))


# Dashboard
class Indexa(Resource):
    @jwt_required()
    def get(self):
        return make_response(render_template("admin/dashboard.html"))


# viewmembers function
class ViewRegisteredmembers(Resource):
    @jwt_required()
    def get(self):
        return make_response(render_template("admin/appusers.html"))

    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('pg', type=str)
        post_parser.add_argument('srch', type=str)
        args = post_parser.parse_args()

        # Setting page, limit and offset variables
        per_page = 10
        if args['pg'] == "":
            page = 1
        else:
            page = int(args['pg'])

        search = args['srch']
        offset = (page - 1) * per_page

        userid = get_jwt_identity()
        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        # Executing a query to get the total number of members
        if search == "":
            sqlt = "SELECT count(*) FROM members WHERE  NOT id = %s AND status='0'"
            cur.execute(sqlt, userid)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT * FROM members WHERE NOT id = %s AND status='0'  LIMIT %s,%s"
            val = (userid, offset, per_page)
            results = cur.execute(sql, val)

        else:
            sqlt = "SELECT count(*) FROM members WHERE NOT id= %s  AND  name LIKE %s AND status='0' "
            sval = (userid, ('%' + search + '%'))
            cur.execute(sqlt, sval)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT * FROM members WHERE NOT id = %s  AND  name LIKE %s AND status='0' LIMIT %s,%s"
            val = (userid, ('%' + search + '%'), offset, per_page)
            results = cur.execute(sql, val)

        if results > 0:
            data = cur.fetchall()
            cur.close()

            return jsonify({
                'totalrecords': total,
                'totalpages': math.ceil(total / per_page),
                'currentpage': page,
                'data': data
            })
        else:
            return jsonify({
                'totalrecords': 0,
                'totalpages': 'null',
                'currentpage': 0,
                'data': 0
            })


# addmembers function
class Registermembers(Resource):
    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('fnames', type=str)
        post_parser.add_argument('email', type=str)
        post_parser.add_argument('phone', type=str)
        args = post_parser.parse_args()

        pwo = PasswordGenerator()
        pwo.minlen = 6
        pwo.maxlen = 6
        passwrd = str(pwo.generate())

        fullname = args['fnames']
        emails = args['email']
        phones = args['phone']

        userid = get_jwt_identity()
        roles = "designer"
        status = '0'

        if fullname and emails and phones:
            if (len(phones) == 10):
                cur = db.connection.cursor(pymysql.cursors.DictCursor)
                sql = "SELECT * FROM members WHERE phone = %s OR email = %s "
                val = (phones, emails)
                results = cur.execute(sql, val)
                if results > 0:
                    data = cur.fetchall()
                    cur.close()
                    msg = '{ "err":"One of the details you entered exists in the system"}'
                    msghtml = json.loads(msg)
                    return msghtml
                else:
                    newtimestamp = int(datetime.datetime.now().timestamp())
                    val = (fullname, emails, passwrd, phones, roles, status, newtimestamp)
                    cur = db.connection.cursor()
                    sql = "INSERT INTO members (name,email,password,phone,role,status,time) VALUES (%s,%s,%s,%s,%s,%s,%s)"
                    cur.execute(sql, val)
                    db.connection.commit()
                    cur.close()

                    sendmailstopple([f'{emails}'],fullname,passwrd)

                    msg = '{ "suc":"member was successfully saved"}'
                    msghtml = json.loads(msg)
                    return msghtml
            else:
                msg = '{ "err":"Phone number entered is invalid"}'
                msghtml = json.loads(msg)
                return msghtml

        else:
            msg = '{ "err":"please fill out all the fields"}'
            msghtml = json.loads(msg)
            return msghtml


# Querymembertoedit
class Editmembers(Resource):
    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('id', type=str)
        args = post_parser.parse_args()

        userid = get_jwt_identity()
        cur = db.connection.cursor(pymysql.cursors.DictCursor)
        if request.method == 'POST':
            cid = args['id']
            sqlec = "SELECT * FROM members WHERE id=%s"
            val = (cid)
            resultsec = cur.execute(sqlec, val)
            if resultsec > 0:
                data = cur.fetchall()
                cur.close()
                return jsonify({'data': data})


# update members
class Updatemembers(Resource):
    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('mid', type=str)
        post_parser.add_argument('fnames', type=str)
        post_parser.add_argument('email', type=str)
        post_parser.add_argument('phone', type=str)
        args = post_parser.parse_args()

        userid = get_jwt_identity()
        cur = db.connection.cursor()

        mid = args['mid']
        fullname = args['fnames']
        emails = args['email']
        phones = args['phone']

        sqlec = "UPDATE members SET name=%s,email=%s,phone=%s WHERE id = %s "
        val = (fullname, emails, phones, mid)
        cur.execute(sqlec, val)
        db.connection.commit()
        results = cur.rowcount
        if results > 0:
            cur.close()
            msg = '{ "suc":"saved successfully"}'
            msghtml = json.loads(msg)
            return msghtml
        else:
            cur.close()
            msg = '{ "err":"no changes"}'
            print(msg)
            msghtml = json.loads(msg)
            return msghtml


# suspendmembers
class Suspendmembers(Resource):
    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('id', type=str)
        args = post_parser.parse_args()

        mid = args['id']

        cur = db.connection.cursor(pymysql.cursors.DictCursor)
        sql = "SELECT * FROM members WHERE id= %s "
        val = (mid)
        results = cur.execute(sql, val)
        if results > 0:
            data = cur.fetchall()
            cur.close()
            status = data[0]['status']
            confirmedstatus = 1 if status == 0 else 0

        cur = db.connection.cursor()
        sqlec = "UPDATE members SET status=%s WHERE id = %s "
        val = (confirmedstatus, mid)
        cur.execute(sqlec, val)
        db.connection.commit()
        results = cur.rowcount
        if results > 0:
            cur.close()
            msg = '{ "suc":"Action taken"}'
            msghtml = json.loads(msg)
            return msghtml
        else:
            cur.close()
            msg = '{ "err":"no changes"}'
            msghtml = json.loads(msg)
            return msghtml


# viewsuspendedmembers function
class Viewsuspendedmembers(Resource):
    @jwt_required()
    def get(self):
        return make_response(render_template("admin/suspension.html"))

    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('pg', type=str)
        post_parser.add_argument('srch', type=str)
        args = post_parser.parse_args()

        # Setting page, limit and offset variables
        per_page = 10
        if args['pg'] == "":
            page = 1
        else:
            page = int(args['pg'])

        search = args['srch']
        offset = (page - 1) * per_page

        userid = get_jwt_identity()
        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        # Executing a query to get the total number of members
        if search == "":
            sqlt = "SELECT count(*) FROM members WHERE  NOT id = %s AND status='1'"
            cur.execute(sqlt, userid)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT * FROM members WHERE NOT id = %s AND status='1'  LIMIT %s,%s"
            val = (userid, offset, per_page)
            results = cur.execute(sql, val)

        else:
            sqlt = "SELECT count(*) FROM members WHERE NOT id= %s  AND  name LIKE %s AND status='1' "
            sval = (userid, ('%' + search + '%'))
            cur.execute(sqlt, sval)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT * FROM members WHERE NOT id = %s  AND  name LIKE %s AND status='1' LIMIT %s,%s"
            val = (userid, ('%' + search + '%'), offset, per_page)
            results = cur.execute(sql, val)

        if results > 0:
            data = cur.fetchall()
            cur.close()

            return jsonify({
                'totalrecords': total,
                'totalpages': math.ceil(total / per_page),
                'currentpage': page,
                'data': data
            })
        else:
            return jsonify({
                'totalrecords': 0,
                'totalpages': 'null',
                'currentpage': 0,
                'data': 0
            })


# Deletemembers
class Deletemember(Resource):
    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('id', type=str)
        args = post_parser.parse_args()

        mid = args['id']
        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        sqlec = "DELETE from members WHERE id = %s AND status='0'"
        val = (mid)
        cur.execute(sqlec, val)
        db.connection.commit()
        cur.close()

        msg = '{ "suc":"Deleted successfully"}'
        msghtml = json.loads(msg)
        return msghtml


# view languages
class ViewLanguages(Resource):
    @jwt_required()
    def get(self):
        return make_response(render_template("admin/languages.html"))

    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('pg', type=str)
        post_parser.add_argument('srch', type=str)
        args = post_parser.parse_args()

        # Setting page, limit and offset variables
        per_page = 10
        if args['pg'] == "":
            page = 1
        else:
            page = int(args['pg'])

        search = args['srch']
        offset = (page - 1) * per_page

        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        # Executing a query to get the total number of languages
        if search == "":
            sqlt = "SELECT count(*) FROM languages "
            cur.execute(sqlt)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT * FROM languages  LIMIT %s,%s"
            val = (offset, per_page)
            results = cur.execute(sql, val)

        else:
            sqlt = "SELECT count(*) FROM languages  WHERE  languagename LIKE %s "
            sval = (('%' + search + '%'))
            cur.execute(sqlt, sval)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT * FROM languages WHERE languagename LIKE %s LIMIT %s,%s"
            val = (('%' + search + '%'), offset, per_page)
            results = cur.execute(sql, val)

        if results > 0:
            data = cur.fetchall()
            cur.close()

            return jsonify({
                'totalrecords': total,
                'totalpages': math.ceil(total / per_page),
                'currentpage': page,
                'data': data
            })
        else:
            return jsonify({
                'totalrecords': 0,
                'totalpages': 'null',
                'currentpage': 0,
                'data': 0
            })


# addlanguage function
class addlanguage(Resource):
    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('lang', type=str)
        args = post_parser.parse_args()

        language = args['lang']

        if language:
            cur = db.connection.cursor(pymysql.cursors.DictCursor)
            sql = "SELECT * FROM languages WHERE languagename = %s "
            val = (language)
            results = cur.execute(sql, val)
            if results > 0:
                cur.close()
                msg = '{ "err":"the language you entered exists in the system"}'
                msghtml = json.loads(msg)
                return msghtml
            else:
                val = (language)
                cur = db.connection.cursor()
                sql = "INSERT INTO languages (languagename ) VALUES (%s)"
                cur.execute(sql, val)
                db.connection.commit()
                cur.close()

                msg = '{ "suc":"language was successfully saved"}'
                msghtml = json.loads(msg)
                return msghtml


        else:
            msg = '{ "err":"please fill out all the fields"}'
            msghtml = json.loads(msg)
            return msghtml


# Delete language
class Deletelanguage(Resource):
    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('id', type=str)
        args = post_parser.parse_args()

        mid = args['id']
        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        sqlec = "DELETE from languages WHERE id = %s"
        val = (mid)
        cur.execute(sqlec, val)
        db.connection.commit()
        cur.close()

        msg = '{ "suc":"Deleted successfully"}'
        msghtml = json.loads(msg)
        return msghtml


# viewbatch function
class viewbatch(Resource):
    @jwt_required()
    def get(self):
        return make_response(render_template("admin/batch.html"))

    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('pg', type=str)
        post_parser.add_argument('srch', type=str)
        args = post_parser.parse_args()

        # Setting page, limit and offset variables
        per_page = 10
        if args['pg'] == "":
            page = 1
        else:
            page = int(args['pg'])

        search = args['srch']
        offset = (page - 1) * per_page

        userid = get_jwt_identity()
        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        # Executing a query to get the total number of nuggetsbatch
        if search == "":
            sqlt = "SELECT count(*) FROM nuggets  ORDER  BY postedon DESC"
            cur.execute(sqlt)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT * FROM nuggets ORDER BY postedon DESC  LIMIT %s,%s"
            val = (offset, per_page)
            results = cur.execute(sql, val)

        else:
            sqlt = "SELECT count(*) FROM nuggets WHERE batchname LIKE %s ORDER BY postedon DESC "
            sval = (('%' + search + '%'))
            cur.execute(sqlt, sval)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT * FROM nuggets WHERE batchname LIKE %s ORDER BY postedon DESC LIMIT %s,%s"
            val = (('%' + search + '%'), offset, per_page)
            results = cur.execute(sql, val)

        if results > 0:
            data = cur.fetchall()
            cur.close()

            return jsonify({
                'totalrecords': total,
                'totalpages': math.ceil(total / per_page),
                'currentpage': page,
                'data': data
            })
        else:
            return jsonify({
                'totalrecords': 0,
                'totalpages': 'null',
                'currentpage': 0,
                'data': 0
            })


# get languages for batch
class languagesforbatch(Resource):
    @jwt_required()
    def post(self):
        userid = get_jwt_identity()
        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        sqlec = "SELECT * FROM languages "
        val = (userid)
        resultsec = cur.execute(sqlec)
        if resultsec > 0:
            data = cur.fetchall()
            cur.close()
            return jsonify({'data': data})
        else:
            json_data_list = []
            json_data = {"languagename": "no language exists"}
            json_data_list.append(json_data)
            # print(json.dumps(json_data_list))
            return jsonify({'data': json_data_list})


# addbatch function
class addbatch(Resource):
    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('batchname', type=str)
        post_parser.add_argument('batch', type=str)
        post_parser.add_argument('language', type=str)
        post_parser.add_argument('priority', type=str)
        post_parser.add_argument('psdlink', type=str)
        args = post_parser.parse_args()

        batchnames = args['batchname']
        batchs = args['batch']
        languages = args['language']
        prioritys = args['priority']
        psdlinks = args['psdlink']

        if batchnames and batchs and languages and prioritys and psdlinks or languages != "no language exists":
            cur = db.connection.cursor(pymysql.cursors.DictCursor)
            sql = "SELECT * FROM nuggets WHERE batchname = %s OR batch = %s "
            val = (batchnames, batchs)
            results = cur.execute(sql, val)
            if results > 0:
                cur.close()
                msg = '{ "err":"One of the batch details you entered exists in the system"}'
                msghtml = json.loads(msg)
                return msghtml
            else:
                newtimestamp = int(datetime.datetime.now().timestamp())
                val = (batchnames, batchs, prioritys, languages, psdlinks, newtimestamp)
                cur = db.connection.cursor()
                sql = "INSERT INTO nuggets (batchname,batch,priority,language,psdlink,postedon) VALUES (%s,%s,%s,%s,%s,%s)"
                cur.execute(sql, val)
                db.connection.commit()
                cur.close()

                msg = '{ "suc":"Batch was successfully saved"}'
                msghtml = json.loads(msg)
                return msghtml

        else:
            msg = '{ "err":"please fill out all the fields"}'
            msghtml = json.loads(msg)
            return msghtml


# Querybatchtoedit
class Editbatch(Resource):
    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('id', type=str)
        args = post_parser.parse_args()

        userid = get_jwt_identity()
        cur = db.connection.cursor(pymysql.cursors.DictCursor)
        if request.method == 'POST':
            cid = args['id']
            sqlec = "SELECT * FROM nuggets WHERE id=%s"
            val = (cid)
            resultsec = cur.execute(sqlec, val)
            if resultsec > 0:
                data = cur.fetchall()
                cur.close()
                return jsonify({'data': data})


# updatebatch
class Updatebatch(Resource):
    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('mid', type=str)
        post_parser.add_argument('batchname', type=str)
        post_parser.add_argument('batch', type=str)
        post_parser.add_argument('language', type=str)
        post_parser.add_argument('priority', type=str)
        post_parser.add_argument('psdlink', type=str)
        args = post_parser.parse_args()

        batchnames = args['batchname']
        batchs = args['batch']
        languages = args['language']
        prioritys = args['priority']
        psdlinks = args['psdlink']
        mid = args['mid']

        cur = db.connection.cursor()

        if languages != "no language exists":
            sqlec = "UPDATE nuggets SET batchname=%s,batch=%s,language=%s,priority=%s,psdlink=%s WHERE id = %s "
            val = (batchnames, batchs, languages, prioritys, psdlinks, mid)
            cur.execute(sqlec, val)
            db.connection.commit()
            results = cur.rowcount
            if results > 0:
                cur.close()
                msg = '{ "suc":"saved successfully"}'
                msghtml = json.loads(msg)
                return msghtml
            else:
                cur.close()
                msg = '{ "err":"no changes"}'
                print(msg)
                msghtml = json.loads(msg)
                return msghtml
        else:
            msg = '{ "err":"please fill out all the fields"}'
            msghtml = json.loads(msg)
            return msghtml


# Delete batch
class Deletebatch(Resource):
    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('id', type=str)
        args = post_parser.parse_args()

        mid = args['id']
        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        sqlec = "DELETE from nuggets WHERE id = %s"
        val = (mid)
        cur.execute(sqlec, val)
        db.connection.commit()
        cur.close()

        msg = '{ "suc":"Deleted successfully"}'
        msghtml = json.loads(msg)
        return msghtml


# viewasignedbatch+ assign function
class asignbatch(Resource):
    @jwt_required()
    def get(self):
        return make_response(render_template("admin/assignbatch.html"))

    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('unbatches', type=str)
        post_parser.add_argument('member', type=str)
        args = post_parser.parse_args()

        unbatch = args['unbatches']
        memberz = args['member']

        if memberz != "no members exists" or unbatch != "no unassigned batch exists":
            sqlec = "SELECT * FROM assignments WHERE member=%s AND nuggett=%s"
            val = (memberz, unbatch)
            cur = db.connection.cursor(pymysql.cursors.DictCursor)
            resultsec = cur.execute(sqlec, val)
            if resultsec > 0:
                cur.close()
                msg = '{ "err":"the batch is already assigned"}'
                print(msg)
                msghtml = json.loads(msg)
                return msghtml

            else:
                newtimestamp = int(datetime.datetime.now().timestamp())
                val = (memberz, unbatch, newtimestamp)
                cur = db.connection.cursor()
                sql = "INSERT INTO assignments (member,nuggett,timeassigned) VALUES (%s,%s,%s)"
                cur.execute(sql, val)
                db.connection.commit()

                sqlec = "UPDATE nuggets SET assigned='1' WHERE id = %s "
                val = (unbatch)
                cur.execute(sqlec, val)
                db.connection.commit()
                results = cur.rowcount
                if results > 0:
                    msg = '{ "suc":"Batch was assigned successfully "}'
                    msghtml = json.loads(msg)
                    return msghtml
                else:
                    cur.close()
                    msg = '{ "err":"no changes"}'
                    print(msg)
                    msghtml = json.loads(msg)
                    return msghtml

        else:
            msg = '{ "err":"please fill out all the fields"}'
            msghtml = json.loads(msg)
            return msghtml


# get members for batchasignment
class membersforbatchasignment(Resource):
    @jwt_required()
    def post(self):
        userid = get_jwt_identity()
        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        sqlec = "SELECT * FROM members WHERE status='0' AND NOT id=%s"
        val = (userid)
        resultsec = cur.execute(sqlec, val)
        if resultsec > 0:
            data = cur.fetchall()
            cur.close()
            return jsonify({'data': data})
        else:
            json_data_list = []
            json_data = {"name": "no members exists"}
            json_data_list.append(json_data)
            # print(json.dumps(json_data_list))
            return jsonify({'data': json_data_list})


# get members for batchasignment
class inncompletebatchforasignment(Resource):
    @jwt_required()
    def post(self):
        userid = get_jwt_identity()
        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        sqlec = "SELECT * FROM nuggets WHERE assigned='0' "
        val = (userid)
        resultsec = cur.execute(sqlec)
        if resultsec > 0:
            data = cur.fetchall()
            cur.close()
            return jsonify({'data': data})
        else:
            json_data_list = []
            json_data = {"batchname": "no unassigned batch exists"}
            json_data_list.append(json_data)
            # print(json.dumps(json_data_list))
            return jsonify({'data': json_data_list})


# batch progress function
class batchprogress(Resource):
    @jwt_required()
    def get(self):
        return make_response(render_template("admin/batchprogress.html"))

    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('pg', type=str)
        post_parser.add_argument('srch', type=str)
        args = post_parser.parse_args()

        # Setting page, limit and offset variables
        per_page = 10
        if args['pg'] == "":
            page = 1
        else:
            page = int(args['pg'])

        search = args['srch']
        offset = (page - 1) * per_page

        # userid = get_jwt_identity()
        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        # Executing a query to get the total number of nuggetsbatch
        if search == "":
            sqlt = "SELECT count(*) FROM ((assignments  INNER JOIN  nuggets ON assignments.nuggett=nuggets.id)  INNER JOIN  members ON assignments.member=members.id ) WHERE assignments.status='0' AND nuggets.assigned='1' ORDER BY assignments.timeassigned DESC"
            cur.execute(sqlt)
            result = cur.fetchone()
            total = result['count(*)']
            print(total)

            sql = "SELECT nuggets.id  As nid,nuggets.batchname,members.id,members.name,assignments.id as aid,assignments.* FROM ((assignments  INNER JOIN  nuggets ON assignments.nuggett=nuggets.id)  INNER JOIN  members ON assignments.member=members.id ) WHERE assignments.status='0' AND nuggets.assigned='1'  ORDER BY assignments.timeassigned DESC  LIMIT %s,%s"
            val = (offset, per_page)
            results = cur.execute(sql, val)
            # print(results)

        else:
            sqlt = "SELECT count(*) FROM ((assignments  INNER JOIN  nuggets ON assignments.nuggett=nuggets.id)  INNER JOIN  members ON assignments.member=members.id ) WHERE assignments.status='0' AND nuggets.assigned='1' AND  nuggets.batchname LIKE %s  ORDER BY assignments.timeassigned DESC"
            sval = (('%' + search + '%'))
            cur.execute(sqlt, sval)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT nuggets.id As nid,nuggets.batchname,members.id,members.name,assignments.id as aid ,assignments.* FROM ((assignments  INNER JOIN  nuggets ON assignments.nuggett=nuggets.id)  INNER JOIN  members ON assignments.member=members.id ) WHERE assignments.status='0' AND nuggets.assigned='1' AND  nuggets.batchname LIKE %s  ORDER BY assignments.timeassigned DESC LIMIT %s,%s"
            val = (('%' + search + '%'), offset, per_page)
            results = cur.execute(sql, val)

        if results > 0:
            data = cur.fetchall()
            cur.close()

            return jsonify({
                'totalrecords': total,
                'totalpages': math.ceil(total / per_page),
                'currentpage': page,
                'data': data
            })
        else:
            return jsonify({
                'totalrecords': 0,
                'totalpages': 'null',
                'currentpage': 0,
                'data': 0
            })


# reassign batch function
class reassignbatch(Resource):
    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('aid', type=str)
        post_parser.add_argument('nid', type=str)
        post_parser.add_argument('mid', type=str)
        post_parser.add_argument('bname', type=str)
        args = post_parser.parse_args()
        aid = args['aid']
        nid = args['nid']
        mid = args['mid']
        bname = args['bname']

        # userid = get_jwt_identity()
        newtimestamp = int(datetime.datetime.now().timestamp())

        cur = db.connection.cursor(pymysql.cursors.DictCursor)
        sqlt = "SELECT * FROM members WHERE id=%s"
        val = (mid)
        cur.execute(sqlt, val)
        result = cur.fetchone()
        name = result['name']

        actionstatement = " Praise THE LORD  " + name + " the batch " + bname + "  that was assigned to you has been reassigned someone else"
        val = (actionstatement, mid, newtimestamp)
        cur = db.connection.cursor()
        sql = "INSERT INTO notifications (notification,directedto,receivedon) VALUES (%s,%s,%s)"
        cur.execute(sql, val)
        db.connection.commit()
        cur.close()

        cur = db.connection.cursor(pymysql.cursors.DictCursor)
        sqlec = "DELETE from assignments WHERE id = %s"
        val = (aid)
        cur.execute(sqlec, val)
        db.connection.commit()
        cur.close()

        cur = db.connection.cursor()
        sqlec = "UPDATE nuggets SET assigned= '0' WHERE id = %s "
        val = (nid)
        cur.execute(sqlec, val)
        db.connection.commit()
        results = cur.rowcount
        if results > 0:
            cur.close()
            msg = '{ "suc":"Assignment removed successfully....press ok to re-assign"}'
            msghtml = json.loads(msg)
            return msghtml
        else:
            cur.close()
            msg = '{ "err":"no changes"}'
            print(msg)
            msghtml = json.loads(msg)
            return msghtml


# finished batch function
class finishedbatch(Resource):
    @jwt_required()
    def get(self):
        return make_response(render_template("admin/finishedbatch.html"))

    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('pg', type=str)
        post_parser.add_argument('srch', type=str)
        args = post_parser.parse_args()

        # Setting page, limit and offset variables
        per_page = 10
        if args['pg'] == "":
            page = 1
        else:
            page = int(args['pg'])

        search = args['srch']
        offset = (page - 1) * per_page

        # userid = get_jwt_identity()
        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        # Executing a query to get the total number of nuggetsbatch
        if search == "":
            sqlt = "SELECT count(*) FROM ((assignments  INNER JOIN  nuggets ON assignments.nuggett=nuggets.id)  INNER JOIN  members ON assignments.member=members.id ) WHERE assignments.status='1' AND nuggets.assigned='1' ORDER BY assignments.timeassigned DESC"
            cur.execute(sqlt)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT nuggets.id  As nid,nuggets.batchname,members.id,members.name,assignments.id as aid,assignments.* FROM ((assignments  INNER JOIN  nuggets ON assignments.nuggett=nuggets.id)  INNER JOIN  members ON assignments.member=members.id ) WHERE assignments.status='1' AND nuggets.assigned='1'  ORDER BY assignments.timeassigned DESC  LIMIT %s,%s"
            val = (offset, per_page)
            results = cur.execute(sql, val)

        else:
            sqlt = "SELECT count(*) FROM ((assignments  INNER JOIN  nuggets ON assignments.nuggett=nuggets.id)  INNER JOIN  members ON assignments.member=members.id ) WHERE assignments.status='1' AND nuggets.assigned='1' AND  nuggets.batchname LIKE %s  ORDER BY assignments.timeassigned DESC"
            sval = (('%' + search + '%'))
            cur.execute(sqlt, sval)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT nuggets.id As nid,nuggets.batchname,members.id,members.name,assignments.id as aid ,assignments.* FROM ((assignments  INNER JOIN  nuggets ON assignments.nuggett=nuggets.id)  INNER JOIN  members ON assignments.member=members.id ) WHERE assignments.status='1' AND nuggets.assigned='1' AND  nuggets.batchname LIKE %s  ORDER BY assignments.timeassigned DESC LIMIT %s,%s"
            val = (('%' + search + '%'), offset, per_page)
            results = cur.execute(sql, val)

        if results > 0:
            data = cur.fetchall()
            cur.close()

            return jsonify({
                'totalrecords': total,
                'totalpages': math.ceil(total / per_page),
                'currentpage': page,
                'data': data
            })
        else:
            return jsonify({
                'totalrecords': 0,
                'totalpages': 'null',
                'currentpage': 0,
                'data': 0
            })


# viewphoto  function
class Viewphoto(Resource):
    @jwt_required()
    def get(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('bid', type=str)
        post_parser.add_argument('mid', type=str)
        args = post_parser.parse_args()
        bid = args['bid']
        mid = args['mid']

        return make_response(render_template("admin/viewphotos.html", bid=bid, mid=mid))

    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('pg', type=str)
        post_parser.add_argument('srch', type=str)
        post_parser.add_argument('bid', type=str)
        post_parser.add_argument('mid', type=str)
        args = post_parser.parse_args()
        bid = args['bid']
        mid = args['mid']

        # Setting page, limit and offset variables
        per_page = 10
        if args['pg'] == "":
            page = 1
        else:
            page = int(args['pg'])

        search = args['srch']
        offset = (page - 1) * per_page

        # userid = get_jwt_identity()
        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        # Executing a query to get the total number of nuggetsbatch
        if search == "":
            sqlt = "SELECT count(*) FROM photos WHERE batchid=%s  AND member= %s ORDER BY submitedtime DESC"
            val = (bid, mid)
            cur.execute(sqlt, val)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT * FROM photos WHERE batchid=%s  AND member=%s ORDER BY submitedtime DESC  LIMIT %s,%s"
            val = (bid, mid, offset, per_page)
            results = cur.execute(sql, val)

        else:
            sqlt = "SELECT count(*)  FROM photos WHERE batchid=%s  AND member= %s AND tag LIKE %s  ORDER BY submitedtime DESC "
            sval = (bid, mid, ('%' + search + '%'))
            cur.execute(sqlt, sval)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT * FROM photos WHERE batchid=%s  AND member= %s AND tag LIKE %s  ORDER BY submitedtime DESC  LIMIT %s,%s"
            val = (bid, mid, ('%' + search + '%'), offset, per_page)
            results = cur.execute(sql, val)

        if results > 0:
            data = cur.fetchall()
            cur.close()

            return jsonify({
                'totalrecords': total,
                'totalpages': math.ceil(total / per_page),
                'currentpage': page,
                'data': data
            })
        else:
            return jsonify({
                'totalrecords': 0,
                'totalpages': 'null',
                'currentpage': 0,
                'data': 0
            })


# check memberbatchtally function
class Memberbatchtally(Resource):
    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('pg', type=str)
        post_parser.add_argument('srch', type=str)
        args = post_parser.parse_args()

        # Setting page, limit and offset variables
        per_page = 10
        if args['pg'] == "":
            page = 1
        else:
            page = int(args['pg'])

        search = args['srch']
        offset = (page - 1) * per_page

        # userid = get_jwt_identity()
        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        # Executing a query to get the total number of nuggetsbatch
        if search == "":
            sqlt = "SELECT members.name, COUNT(DISTINCT  batchid) AS nugg FROM members LEFT JOIN photos ON photos.member = members.id GROUP BY name ORDER BY nugg DESC"
            total = cur.execute(sqlt)

            sql = "SELECT members.name, COUNT(DISTINCT batchid) AS nugg FROM members LEFT JOIN photos ON photos.member = members.id GROUP BY name ORDER BY nugg DESC LIMIT %s,%s"
            val = (offset, per_page)
            results = cur.execute(sql, val)

        else:
            sqlt = "SELECT members.name, COUNT(DISTINCT batchid) AS nugg FROM members LEFT JOIN photos ON photos.member = members.id  GROUP BY name  HAVING members.name LIKE %s ORDER BY nugg DESC"
            sval = (('%' + search + '%'))
            total = cur.execute(sqlt, sval)

            sql = "SELECT members.name, COUNT(DISTINCT  batchid) AS nugg FROM members LEFT JOIN photos ON photos.member = members.id  GROUP BY name  HAVING members.name LIKE %s ORDER BY nugg DESC  LIMIT %s,%s"
            val = (('%' + search + '%'), offset, per_page)
            results = cur.execute(sql, val)

        if results > 0:
            data = cur.fetchall()
            cur.close()

            return jsonify({
                'totalrecords': total,
                'totalpages': math.ceil(total / per_page),
                'currentpage': page,
                'data': data
            })
        else:
            return jsonify({
                'totalrecords': 0,
                'totalpages': 'null',
                'currentpage': 0,
                'data': 0
            })


# check notificationdashboard function
class notificationdashboard(Resource):
    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('pg', type=str)
        post_parser.add_argument('srch', type=str)
        args = post_parser.parse_args()

        # Setting page, limit and offset variables
        per_page = 10
        if args['pg'] == "":
            page = 1
        else:
            page = int(args['pg'])

        search = args['srch']
        offset = (page - 1) * per_page

        # userid = get_jwt_identity()
        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        # Executing a query to get the total number of nuggetsbatch
        if search == "":
            sqlt = "SELECT count(*) FROM notifications WHERE directedto='1' ORDER BY receivedon DESC"
            cur.execute(sqlt)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT * FROM notifications WHERE directedto='1' ORDER BY receivedon DESC LIMIT %s,%s"
            val = (offset, per_page)
            results = cur.execute(sql, val)

        if results > 0:
            data = cur.fetchall()
            cur.close()

            return jsonify({
                'totalrecords': total,
                'totalpages': math.ceil(total / per_page),
                'currentpage': page,
                'data': data
            })
        else:
            return jsonify({
                'totalrecords': 0,
                'totalpages': 'null',
                'currentpage': 0,
                'data': 0
            })


# check notification function
class checknotification(Resource):
    @jwt_required()
    def get(self):
        return make_response(render_template("admin/viewnotification.html"))

    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('pg', type=str)
        post_parser.add_argument('srch', type=str)
        args = post_parser.parse_args()

        # Setting page, limit and offset variables
        per_page = 10
        if args['pg'] == "":
            page = 1
        else:
            page = int(args['pg'])

        search = args['srch']
        offset = (page - 1) * per_page

        # userid = get_jwt_identity()
        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        # Executing a query to get the total number of nuggetsbatch
        if search == "":
            sqlt = "SELECT count(*) FROM notifications WHERE directedto='1' ORDER BY receivedon DESC"
            cur.execute(sqlt)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT * FROM notifications WHERE directedto='1' ORDER BY receivedon DESC LIMIT %s,%s"
            val = (offset, per_page)
            results = cur.execute(sql, val)

        if results > 0:
            data = cur.fetchall()
            cur.close()

            return jsonify({
                'totalrecords': total,
                'totalpages': math.ceil(total / per_page),
                'currentpage': page,
                'data': data
            })
        else:
            return jsonify({
                'totalrecords': 0,
                'totalpages': 'null',
                'currentpage': 0,
                'data': 0
            })


# dashboard function
class dashboarddata(Resource):
    @jwt_required()
    def post(self):
        # userid = get_jwt_identity()
        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        sql = "select (select count(*) from members) as mem, (select count(*) from photos) as ph,(select count(*) from languages) as lang"
        results = cur.execute(sql)

        if results > 0:
            data = cur.fetchall()
            cur.close()

            return jsonify({
                'totalrecords': results,
                'totalpages': 0,
                'currentpage': 0,
                'data': data
            })
        else:
            return jsonify({
                'totalrecords': 0,
                'totalpages': 'null',
                'currentpage': 0,
                'data': 0
            })


# downloadpic function
class Downloadpic(Resource):
    def get(self, filename):
        filepath = safe_join(app.config['UPLOAD_FOLDER'], filename)

        response = send_file(
            path_or_file=filepath,
            mimetype="application/octet-stream",
            as_attachment=True,
            attachment_filename=filename
        )
        return response


# seeingbatch function
class Seeingbatch(Resource):
    @jwt_required()
    def get(self):
      return make_response(render_template("admin/seenuggets.html"))

# profilenames
class adminprofile(Resource):

    @jwt_required()
    def post(self):
        userid = get_jwt_identity()

        cur = db.connection.cursor(pymysql.cursors.DictCursor)
        sqlt = "SELECT * FROM members WHERE id=%s"
        val = (userid)
        cur.execute(sqlt, val)
        result = cur.fetchone()
        name = result['name']
        phone = result['phone']
        email = result['email']
        js = [{'name': name, 'phone': phone, 'email': email}]
        return json.dumps(js)


# addnotification function
class addnotifiction(Resource):
    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('action', type=str)
        post_parser.add_argument('mid', type=str)
        args = post_parser.parse_args()

        action = args['action']
        mid = args['mid']

        # userid = get_jwt_identity()
        newtimestamp = int(datetime.datetime.now().timestamp())

        cur = db.connection.cursor(pymysql.cursors.DictCursor)
        sqlt = "SELECT * FROM members WHERE id=%s"
        val = (mid)
        cur.execute(sqlt, val)
        result = cur.fetchone()
        name = result['name']

        actionstatement = " Praise THE LORD  " + name + " you have been  " + action
        val = (actionstatement, mid, newtimestamp)
        cur = db.connection.cursor()
        sql = "INSERT INTO notifications (notification,directedto,receivedon) VALUES (%s,%s,%s)"
        cur.execute(sql, val)
        db.connection.commit()
        cur.close()


# refreshing expired tokens
class Tokenrfrsh(Resource):

    @jwt_required(refresh=True)
    def get(self):
        # Refreshing expired Access token
        user_id = get_jwt_identity()
        access_token = create_access_token(identity=str(user_id), fresh=True)
        resp = make_response(redirect('/admin/Dashboard', 302))
        set_access_cookies(resp, access_token)
        return resp


# logout
class Logouta(Resource):
    def get(self):
        # Revoke Fresh/Non-fresh Access and Refresh tokens
        return unset_jwt()


api.add_resource(Login, '/')
api.add_resource(Indexa, '/Dashboard')
api.add_resource(ViewRegisteredmembers, '/registermembers')
api.add_resource(Registermembers, '/addmembers')
api.add_resource(Editmembers, '/editmembers')
api.add_resource(Updatemembers, '/updatemembers')
api.add_resource(Suspendmembers, '/suspendmembers')
api.add_resource(Viewsuspendedmembers, '/viewsuspendmembers')
api.add_resource(Deletemember, '/deletemembers')
api.add_resource(ViewLanguages, '/languages')
api.add_resource(addlanguage, '/addlanguages')
api.add_resource(Deletelanguage, '/deletelanguages')
api.add_resource(viewbatch, '/viewbatch')
api.add_resource(languagesforbatch, '/languageforbatch')
api.add_resource(addbatch, '/addbatch')
api.add_resource(Editbatch, '/editbatch')
api.add_resource(Updatebatch, '/updatebatch')
api.add_resource(Deletebatch, '/deletebatch')
api.add_resource(asignbatch, '/viewassignedbatch')
api.add_resource(membersforbatchasignment, '/membersforbatchasignment')
api.add_resource(inncompletebatchforasignment, '/inncompletebatchforasignment')
api.add_resource(batchprogress, '/batchprogress')
api.add_resource(reassignbatch, '/reassignbatch')
api.add_resource(finishedbatch, '/finishedbatch')
api.add_resource(Viewphoto, '/Viewphoto')
api.add_resource(Memberbatchtally, '/Memberbatchtally')
api.add_resource(notificationdashboard, '/notificationdashboard')
api.add_resource(checknotification, '/checknotification')
api.add_resource(dashboarddata, '/dashboarddata')
api.add_resource(Downloadpic, '/<string:filename>')
api.add_resource(Seeingbatch, '/seebatch')
api.add_resource(adminprofile, '/adminprofile')
api.add_resource(addnotifiction, '/addnotifiction')
api.add_resource(Tokenrfrsh, '/refreshingtokens')
api.add_resource(Logouta, '/signout')
