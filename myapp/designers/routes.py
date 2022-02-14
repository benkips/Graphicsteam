from functools import wraps

import werkzeug
from flask_restful import reqparse, Resource
from myapp.extension import api, jwt
import datetime
import math
import os


import pymysql
from flask import Blueprint, render_template, make_response, request, jsonify, json, redirect, url_for, session, \
    current_app as app
from werkzeug.utils import secure_filename
from myapp.extension import db
from flask_mail import  Message
from myapp.extension import mail
from flask_jwt_extended import (jwt_required, get_jwt_identity,
                                create_access_token, create_refresh_token,
                                set_access_cookies, set_refresh_cookies,
                                unset_jwt_cookies, unset_access_cookies, get_jwt)
from PIL import Image

designers = Blueprint('designers', __name__, url_prefix="/designers", template_folder='templates')
api.init_app(designers)

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

# resize pic
def resizetool(fullpath):
    small = 540, 540

    ### small THUMBNAIL ###
    thumbnail_image = Image.open(fullpath)
    thumbnail_image.thumbnail(small, Image.LANCZOS)
    thumbnail_image.save(fullpath, optimize=True, quality=95)

def checknames(names):
    listofnames = " ".join(names.split())
    return listofnames.split(" ")[0]

def sendmailstopple(contacts, passw):
        with mail.connect() as conn:
            for email in contacts:
                message = f'Your requested password is {passw}'
                subject = "Password Reset for mamafua app"
                msg = Message(recipients=[email], sender=f'Media feeds<mediafeeds@ekarantechnologies.com>', \
                              body=message, subject=subject, reply_to='mediafeeds@ekarantechnologies.com')
                conn.send(msg)
                print(f'sent to {email}')

# check if extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# delete file
def deleteany_file(filename):
    os.unlink(os.path.join(app.config['UPLOAD_FOLDER'], filename))



def assign_access_refresh_tokens(user_id, url):
    access_token = create_access_token(identity=str(user_id), fresh=True)
    refresh_token = create_refresh_token(identity=str(user_id))
    resp = make_response(redirect(url, 302))
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)
    return resp


def unset_jwt():
    resp = make_response(redirect('/designers/login', 302))
    unset_jwt_cookies(resp)
    return resp


# login function
class Loginb(Resource):
    def get(self):
        return make_response(render_template("designers/login.html"))

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
                role=data[0]['role']
                status=data[0]['status']
                if status == 0:
                    error = 'Kindly visit the admin account'
                    return assign_access_refresh_tokens(pid,'/designers/index') if role=="designer" else make_response(render_template('designers/login.html', error=error))
                else:
                    error = 'Account suspended,contact 254711114002'
                    return make_response(render_template('designers/login.html', error=error))


            else:
                cur.close()
                error = 'username and password could not match'
                return make_response(render_template('designers/login.html', error=error))

        else:
            error = 'Enter the required field'
            return make_response(render_template('designers/login.html', error=error))


class Indexb(Resource):
    @jwt_required()
    def get(self):
        return make_response(render_template("designers/dashboard.html"))


class  Uploadz(Resource):
    @jwt_required()
    def get(self):
        return make_response(render_template("designers/upload.html"))

    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('asbatches', type=str)
        post_parser.add_argument('tags', type=str)
        post_parser.add_argument('uploadedfile', type=werkzeug.datastructures.FileStorage, location='files')
        args = post_parser.parse_args()

        file = args['uploadedfile']
        abatches = args['asbatches']
        tagz = args['tags']
        userid = get_jwt_identity()

        filename = secure_filename(file.filename)
        extension = filename.split(".")[-1]
        newtimestamp = int(datetime.datetime.now().timestamp())
        file.filename = str(newtimestamp) + "." + str(extension)
        filerenamed = file.filename

        if file and allowed_file(filerenamed) and abatches != "no assignments pending" and tagz:
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filerenamed))

            val = (filerenamed,abatches,userid,newtimestamp,tagz)
            cur = db.connection.cursor()
            sql = "INSERT INTO photos (picture,batchid,member,submitedtime,tag) VALUES (%s,%s,%s,%s,%s)"
            cur.execute(sql, val)
            db.connection.commit()

            msg = '{ "suc":"image uploaded successfully thank you"}'
            msghtml = json.loads(msg)
            return msghtml
        else:
            msg = '{ "err":"there exists a problem  check file extension try again"}'
        msghtml = json.loads(msg)
        return msghtml

# get membersasignments
class membersasignments(Resource):
    @jwt_required()
    def post(self):
        userid = get_jwt_identity()
        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        sqlec ="SELECT nuggets.id,nuggets.batchname FROM nuggets LEFT JOIN assignments ON nuggets.id=assignments.nuggett WHERE assignments.member=%s AND nuggets.assigned='1' AND assignments.status='0'"
        val = (userid)
        resultsec = cur.execute(sqlec,val)
        if resultsec > 0:
            data = cur.fetchall()
            cur.close()
            return jsonify({'data': data})
        else:
            json_data_list = []
            json_data = { "batchname":"no assignments pending"}
            json_data_list.append(json_data)
            # print(json.dumps(json_data_list))
            return jsonify({'data': json_data_list})

# viewassignments function
class viewassignments(Resource):
    @jwt_required()
    def get(self):
        return make_response(render_template("designers/viewassignment.html"))

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
            sqlt = "SELECT count(*) FROM ((assignments  INNER JOIN  nuggets ON assignments.nuggett=nuggets.id)  INNER JOIN  members ON assignments.member=members.id ) WHERE assignments.status='0' AND nuggets.assigned='1' AND assignments.member=%s ORDER BY assignments.timeassigned DESC"
            val=(userid)
            cur.execute(sqlt,val)
            result = cur.fetchone()
            total = result['count(*)']
            print(total)

            sql = "SELECT nuggets.id  As nid,nuggets.batchname,nuggets.batch,members.id,members.name,assignments.id as aid,assignments.* FROM ((assignments  INNER JOIN  nuggets ON assignments.nuggett=nuggets.id)  INNER JOIN  members ON assignments.member=members.id ) WHERE assignments.status='0' AND nuggets.assigned='1' AND assignments.member=%s  ORDER BY assignments.timeassigned DESC  LIMIT %s,%s"
            val = (userid,offset, per_page)
            results = cur.execute(sql, val)
            # print(results)

        else:
            sqlt = "SELECT count(*) FROM ((assignments  INNER JOIN  nuggets ON assignments.nuggett=nuggets.id)  INNER JOIN  members ON assignments.member=members.id ) WHERE assignments.status='0' AND nuggets.assigned='1' AND  nuggets.batchname LIKE %s AND assignments.member=%s ORDER BY assignments.timeassigned DESC"
            sval = (('%' + search + '%'),userid)
            cur.execute(sqlt, sval)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT nuggets.id As nid,nuggets.batchname,nuggets.batch,members.id,members.name,assignments.id as aid ,assignments.* FROM ((assignments  INNER JOIN  nuggets ON assignments.nuggett=nuggets.id)  INNER JOIN  members ON assignments.member=members.id ) WHERE assignments.status='0' AND nuggets.assigned='1' AND  nuggets.batchname LIKE %s AND assignments.member=%s  ORDER BY assignments.timeassigned DESC LIMIT %s,%s"
            val = (('%' + search + '%'),userid, offset, per_page)
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

# markascomplete function
class markascomplete(Resource):
    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('aid', type=str)
        post_parser.add_argument('nid', type=str)
        args = post_parser.parse_args()
        aid = args['aid']
        nid = args['nid']


        cur = db.connection.cursor()
        sqlec = "UPDATE assignments SET status='1' WHERE id = %s "
        val = (aid)
        cur.execute(sqlec, val)
        db.connection.commit()
        results = cur.rowcount
        if results > 0:
            cur.close()
            msg = '{ "suc":"Updated successfully"}'
            msghtml = json.loads(msg)
            return msghtml
        else:
            cur.close()
            msg = '{ "err":"no changes"}'
            print(msg)
            msghtml = json.loads(msg)
            return msghtml

# finished batch function
class finishedassignements(Resource):
    @jwt_required()
    def get(self):
        return make_response(render_template("designers/myfinishedbatch.html"))

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
            sqlt = "SELECT count(*) FROM ((assignments  INNER JOIN  nuggets ON assignments.nuggett=nuggets.id)  INNER JOIN  members ON assignments.member=members.id ) WHERE assignments.status='1' AND nuggets.assigned='1'AND assignments.member=%s ORDER BY assignments.timeassigned DESC"
            val = (userid)
            cur.execute(sqlt,val)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT nuggets.id  As nid,nuggets.batchname,nuggets.psdlink,members.id,members.name,assignments.id as aid,assignments.* FROM ((assignments  INNER JOIN  nuggets ON assignments.nuggett=nuggets.id)  INNER JOIN  members ON assignments.member=members.id ) WHERE assignments.status='1' AND nuggets.assigned='1' AND assignments.member=%s  ORDER BY assignments.timeassigned DESC  LIMIT %s,%s"
            val = (userid,offset, per_page)
            results = cur.execute(sql, val)

        else:
            sqlt = "SELECT count(*) FROM ((assignments  INNER JOIN  nuggets ON assignments.nuggett=nuggets.id)  INNER JOIN  members ON assignments.member=members.id ) WHERE assignments.status='1' AND nuggets.assigned='1' AND  nuggets.batchname LIKE %s AND assignments.member=%s  ORDER BY assignments.timeassigned DESC"
            sval = (('%' + search + '%'), userid)
            cur.execute(sqlt, sval)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT nuggets.id As nid,nuggets.batchname,members.id,members.name,nuggets.psdlink,assignments.id as aid ,assignments.* FROM ((assignments  INNER JOIN  nuggets ON assignments.nuggett=nuggets.id)  INNER JOIN  members ON assignments.member=members.id ) WHERE assignments.status='1' AND nuggets.assigned='1' AND  nuggets.batchname LIKE %s AND assignments.member=%s  ORDER BY assignments.timeassigned DESC LIMIT %s,%s"
            val = (('%' + search + '%'), userid, offset, per_page)
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


# markasuncomplete function
class markasuncomplete(Resource):
    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('aid', type=str)
        post_parser.add_argument('nid', type=str)
        args = post_parser.parse_args()
        aid = args['aid']
        nid = args['nid']


        cur = db.connection.cursor()
        sqlec = "UPDATE assignments SET status='0' WHERE id = %s "
        val = (aid)
        cur.execute(sqlec, val)
        db.connection.commit()
        results = cur.rowcount
        if results > 0:
            cur.close()
            msg = '{ "suc":"Updated successfully"}'
            msghtml = json.loads(msg)
            return msghtml
        else:
            cur.close()
            msg = '{ "err":"no changes"}'
            print(msg)
            msghtml = json.loads(msg)
            return msghtml

# viewphoto  function
class Viewphotoz(Resource):
    @jwt_required()
    def get(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('bid', type=str)
        post_parser.add_argument('mid', type=str)
        args = post_parser.parse_args()
        bid=args['bid']
        mid=args['mid']

        return make_response(render_template("designers/viewphotoz.html",bid=bid,mid=mid))

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
            cur.execute(sqlt,val)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT * FROM photos WHERE batchid=%s  AND member=%s ORDER BY submitedtime DESC  LIMIT %s,%s"
            val = (bid,mid,offset, per_page)
            results = cur.execute(sql, val)

        else:
            sqlt = "SELECT count(*)  FROM photos WHERE batchid=%s  AND member= %s AND tag LIKE %s  ORDER BY submitedtime DESC "
            sval = (bid, mid,('%' + search + '%'))
            cur.execute(sqlt, sval)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT * FROM photos WHERE batchid=%s  AND member= %s AND tag LIKE %s  ORDER BY submitedtime DESC  LIMIT %s,%s"
            val = (bid, mid,('%' + search + '%'), offset, per_page)
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

# Deletephoto function
class Deletephotos(Resource):
    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('pid', type=str)
        args = post_parser.parse_args()
        pid = args['pid']

        cur = db.connection.cursor(pymysql.cursors.DictCursor)
        sqlec = "SELECT * FROM photos WHERE id = %s"
        val = (pid)
        cur.execute(sqlec, val)
        data = cur.fetchone()
        imagedelete = data['picture']
        deleteany_file(imagedelete)

        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        sqlec = "DELETE FROM photos WHERE id = %s"
        val = (pid)
        cur.execute(sqlec, val)
        db.connection.commit()
        cur.close()

        msg = '{ "suc":"Deleted successfully"}'
        msghtml = json.loads(msg)
        return msghtml

# profilenames
class myprofile(Resource):

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

#addnotificationtoadmin function
class addnotifictiontoadmin(Resource):
    @jwt_required()
    def post(self):
        post_parser = reqparse.RequestParser()
        post_parser.add_argument('action', type=str)
        post_parser.add_argument('mid', type=str)
        args = post_parser.parse_args()

        action= args['action']
        mid= args['mid']

        userid = get_jwt_identity()
        newtimestamp = int(datetime.datetime.now().timestamp())

        cur = db.connection.cursor(pymysql.cursors.DictCursor)
        sqlt = "SELECT * FROM members WHERE id=%s"
        val = (userid)
        cur.execute(sqlt, val)
        result = cur.fetchone()
        name = result['name']

        actionstatement=name +" "+ action
        val = (actionstatement,mid,newtimestamp)
        cur = db.connection.cursor()
        sql = "INSERT INTO notifications (notification,directedto,receivedon) VALUES (%s,%s,%s)"
        cur.execute(sql, val)
        db.connection.commit()
        cur.close()

# dashboard function
class dashboarddatadesigner(Resource):
    @jwt_required()
    def post(self):
        userid = get_jwt_identity()
        cur = db.connection.cursor(pymysql.cursors.DictCursor)

        sql = "select (select count(DISTINCT nuggett) from assignments WHERE member=%s) as mem , (select count(*) from photos WHERE member=%s) as ph,(select count(*) from languages) as lang"
        val = (userid,userid)
        results = cur.execute(sql,val)



        if results > 0:
            data = cur.fetchall()
            cur.close()

            return jsonify({
                'totalrecords': results,
                'totalpages': 0,
                'currentpage':0,
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
class notificationdashboarddesigner(Resource):
    @jwt_required()
    def get(self):
        return make_response(render_template("designers/viewnotificationdesignerz.html"))

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
            sqlt = "SELECT count(*) FROM notifications WHERE directedto=%s ORDER BY receivedon DESC"
            val = (userid)
            cur.execute(sqlt,val)
            result = cur.fetchone()
            total = result['count(*)']

            sql = "SELECT * FROM notifications WHERE directedto=%s ORDER BY receivedon DESC LIMIT %s,%s"
            val = (userid,offset, per_page)
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


# seeingbatch function
class Seeingnugg(Resource):
    @jwt_required()
    def get(self):
        post_parser = reqparse.RequestParser()

        post_parser.add_argument('bname', type=str)
        args = post_parser.parse_args()
        bname = args['bname']
        return make_response(render_template("designers/seenuggets.html", bname=bname))


class Toknrfrsh(Resource):

    @jwt_required(refresh=True)
    def get(self):
        # Refreshing expired Access token
        user_id = get_jwt_identity()
        access_token = create_access_token(identity=str(user_id),fresh=True)
        resp = make_response(redirect('/designers/index', 302))
        set_access_cookies(resp, access_token)
        return resp

class Logout(Resource):

    def get(self):
        # Revoke Fresh/Non-fresh Access and Refresh tokens
        return unset_jwt()


api.add_resource(Loginb, '/login')
api.add_resource(Indexb, '/index')
api.add_resource(Uploadz, '/uploads')
api.add_resource(membersasignments, '/membersasignments')
api.add_resource(viewassignments, '/viewassignments')
api.add_resource(markascomplete, '/markascomplete')
api.add_resource(finishedassignements, '/finishedassignements')
api.add_resource(markasuncomplete, '/markasuncomplete')
api.add_resource(Viewphotoz, '/Viewphotoz')
api.add_resource(Deletephotos, '/deletephotos')
api.add_resource(myprofile, '/myprofile')
api.add_resource(addnotifictiontoadmin, '/addnotifictiontoadmin')
api.add_resource(dashboarddatadesigner, '/dashboarddatadesigner')
api.add_resource(notificationdashboarddesigner, '/notificationdashboarddesigner')
api.add_resource(Seeingnugg, '/seenugg')
api.add_resource(Toknrfrsh, '/refreshtokens')
api.add_resource(Logout,'/logout')

