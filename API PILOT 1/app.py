from datetime import datetime
from dis import dis
from turtle import distance

from bson.json_util import dumps
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from pymongo.errors import DuplicateKeyError
from string import Template
from geopy.distance import geodesic
import ast
import json


from db import neg_info, save_param2,sign_contract,change_status, get_neg,owned_auctions,get_bidders,find_rooms,distance_calc,ended,get_template,get_t,get_distance,get_room_admin,save_param,add_room_member,add_room_members, save_room2,update_bid, get_closing,get_hb,get_sign,get_hbidder, get_messages, get_room, get_room_members, get_rooms_for_user, get_user, is_room_admin, is_room_member, remove_room_members, save_message, save_room, save_user, update_room

app = Flask(__name__)


cors = CORS(app)
app.secret_key = "sfdjkafnk"
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


# The login route receives the username and password as a POST request

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return {"message":"The user {} is already authenticated".format(current_user)},200

    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password_input = request.form.get('password')
        user = get_user(username)

        if user and user.check_password(password_input):
            login_user(user)
           
            return {"message":"User {} has been authenticated".format(str(user.username))},200
        else:
            message = 'Failed to login!'
    return message,400


# Signup function is not habilitated for the time being, users are to be created either
# by function or directly into the database

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    message = ''
    if request.method == 'POST':
        username = request.json.get('username')
        email = request.json.get('email')
        password = request.json.get('password')
        sign=request.json.get('sign')
        location=request.json.get('sign')
        try:
            save_user(username, email, password,sign,location)
            return redirect(url_for('login'))
        except DuplicateKeyError:
            message = "User already exists!"
    return render_template('signup.html', message=message)

##holi={"room_name":"Erics composite auction","members":"","highest_bid":"5000","auction_type":"Ascending","closing_time":"2021-07-06T10:34:20","reference_sector":"Composites","reference_type":"Electronic","quantity":"15","templatetype":"article","articleno":"23dd"}


# A request to this function will log out the user from the server

@app.route("/logout/")
@login_required
def logout():
    logout_user()
    return {'message':'the user has logged out'},200


# Use a POST request to create a new auction, user has to be logged in

@app.route('/create-room', methods=['GET', 'POST'])
#@login_required
def create_room():
    if request.method == 'POST':
        privacy= request.form.get('privacy')
        room_name = request.form.get('room_name')
        print(room_name)
        highest_bid=request.form.get('highest_bid')
        highest_bidder=''
        auction_type=request.form.get('auction_type')
        print(request.form.get('closing_time'))
        closing_time=datetime.strptime(request.form.get('closing_time'), '%Y-%m-%dT%H:%M:%S')
        reference_sector=request.form.get('reference_sector')
        reference_type=request.form.get('reference_type')
        quantity=request.form.get('quantity')
        articleno=request.form.get('articleno')
        user=request.authorization.username
        print(user)
        sellersign=get_sign(user)
        buyersign=''
        templatetype=request.form.get('templatetype')
        print(templatetype)
        print(request.form.get('members'))
        if(request.form.get('members')):
            usernames = [username.strip() for username in request.form.get('members').split(',')]
        else: 
            print(user)
            usernames=[user]

        if len(room_name) and len(usernames):
                      
            room_id = save_room(privacy, room_name, user,auction_type,highest_bid,highest_bidder,closing_time,sellersign,buyersign,templatetype)
            save_param(room_id,user,room_name,reference_sector,reference_type,quantity,articleno)
            if user in usernames:
                usernames.remove(user)
            print(len(usernames))
            if len(usernames)>=1:
                print('hay')
                print('usernames')
                add_room_members(room_id, room_name, usernames, user)
            return {"message":"The room {} has been created id: {}".format(str(room_name),room_id)},200
        else:
            return {"message":"Unable to create room"},400


# Edit room also is not enabled but should work with little effort if needed

@app.route('/rooms/<room_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_room(room_id):
    room = get_room(room_id)
    if room and is_room_admin(room_id, current_user.username):
        existing_room_members = [member['_id']['username'] for member in get_room_members(room_id)]
        room_members_str = ",".join(existing_room_members)
        message = ''
        if request.method == 'POST':
            room_name = request.json.get('room_name')
            room['name'] = room_name
            update_room(room_id, room_name)

            new_members = [username.strip() for username in request.json.get('members').split(',')]
            members_to_add = list(set(new_members) - set(existing_room_members))
            members_to_remove = list(set(existing_room_members) - set(new_members))
            if len(members_to_add):
                add_room_members(room_id, room_name, members_to_add, current_user.username)
            if len(members_to_remove):
                remove_room_members(room_id, members_to_remove)
            message = 'Room edited successfully'
            room_members_str = ",".join(new_members)
        return render_template('edit_room.html', room=room, room_members_str=room_members_str, message=message)
    else:
        return "Room not found", 404


# GET request to this route has to include room_id for the room you want to join but no aditional parameters are needed

@app.route('/rooms/<room_id>/join', methods=['GET'])
#@login_required
def join_room(room_id):
    room = get_room(room_id)
    room_name=room['payload']['name']['val'][0]
    user=request.authorization.username

    existing_room_members = [member['_id']['username'] for member in get_room_members(room_id)]
    if request.method == 'GET':
        new_members = user
        if new_members in list(set(existing_room_members)):
            return {"message":"You are already in a room"},200
        add_room_member(room_id, room_name, new_members, user)

        
    return {"message":"You have joined the room {}".format(str(room_name))},200




# A POST request to this route will receive parameter message_input and will generate a bid to the auction
# A GET request will show all the messages submited to this auction.

@app.route('/rooms/<room_id>', methods=['GET','POST'])
#@login_required
def chat(room_id):
    room = get_room(room_id)
    rn=room['payload']['name']['val'][0]
    closing_time=get_closing(room_id)
    user=request.authorization.username

    if room and is_room_member(room_id, user):
        
        ## The event for the timeout message could go here
        
        if request.method=='POST':
            bid=request.form.get("message_input")
            if (closing_time)>datetime.now():
                print(is_room_admin(room_id,user))
                if(is_room_admin(room_id,user)==0):
                    app.logger.info("{} has summited a new bid to the room {}: {}".format(user,
                                                                            rn,
                                                                            bid))
                    sign=get_sign(user)
                    ## Calculation of distance between users done at every bid
                    print(user,get_room_admin(rn))
                    distance=distance_calc(user,get_room_admin(rn))
                    #
                    save_message(str(room['_id']),bid,user,sign,distance)                    
                else:
                    app.logger.info("Cannot bid if you are Admin")  
                    return{"message":"You cannot issue bids as room admin"},400                          
            else:
                app.logger.info("Auction time has ended")
                return {"message":"The auction {} has already ended".format(str(rn))},400
            return {"message":"You have issued the bid {}".format(str(bid))},200
        elif request.method=='GET':
            messages = get_messages(room_id)
            if room and is_room_member(room_id, user):
                
                ## Here the bids from all users are shown to the user 
                
                keys = ['sender','text', 'created_at','distance']
                d=[]
                for message in messages:
                    m_pay=message['payload']
                    filtered_d = dict((k, m_pay[k]) for k in keys if k in m_pay)
                    d.append(filtered_d)

                body = {"Bids": d}
                
                return jsonify(body),200

    else:
        return "Room not found or user is not member", 404


# A POST request to this auction is used to select the winner with the paremeter "winner" only in case no winner is selected yet
# A GET request in case the auction isnt ended will display the highest bids from all the biders
# and will show the ricardian contract in case the auction is ended

@app.route('/rooms/<room_id>/end', methods=['GET','POST'])
##@login_required
def winner(room_id):
    
    closing_time=get_closing(room_id)
    
    room = get_room(room_id)
    
    rn=room['payload']['name']['val'][0]
    
    user=request.authorization.username
## Withing this function the logic for the winner selection is specified, the admin shall input the username of the winner
    if request.method=='POST':
        
        if(is_room_admin(room_id,user)==1):
            
            #if (closing_time)>datetime.now(): #Auction hasnt ended
                    #return{"message":"The specified auction hasnt ended"},400
            if get_hbidder(room_id)=='': ## This would mean the auction doesnt have a winner yet
                winner=request.form.get("winner") #Should be username
                wi=json.loads(get_hb(room_id,winner)) ## Get hb should be changed in case the auction is descending
                if wi:
                    for d in wi:
                        sen=d['sender']
                        bid=d['text']
                        sign=d['sign']
                    update_bid(room['_id'],bid,sen,sign)
                    return {"message":"winner has been selected"},200
                else: 
                    return {"message":"User does not participate the auction"},403
            else: 
                return {"message":"the winner for this auciton has already been selected"},200
        else: return{"message":"You are not room admin"},400
    elif request.method=='GET':
        print()
        if user == get_room_admin(rn):
            if get_hbidder(room_id)=='': #Winner hasnt been selected
                return get_bidders(room_id),200
            else: #Winner is selected
                response={'contract':ended(room_id)}
                return jsonify(response),200
        elif (user==get_hbidder(room_id)):
            response={'contract':ended(room_id)}
            return jsonify(response),200
        elif get_hbidder(room_id)=='':
            return {"message":"Winner hasnt been selected"},400
        else: 
            return {"message":"The auction has ended, the winner is {}".format(room['highest_bidder'])},400


            
# A GET request to this route is used to query auction based in the parameters listed below

@app.route('/rooms', methods=['GET'])
#@login_required
def query():
    if request.method=='GET':
        user=request.authorization.username
        room_name=request.json.get("room_name")
        reference_sector=request.json.get("reference_sector")
        reference_type=request.json.get("reference_type")
        ongoing=request.json.get("ongoing")
        distance= request.json.get("distance")
        print(distance, user)
        auctions=find_rooms(room_name,reference_sector,reference_type,ongoing,user,distance)
        return auctions,200


@app.route('/myrooms/admin',methods=['GET'])
def myauct_a():
    if request.method=='GET':
        user=request.authorization.username
        owner=True
        auct=owned_auctions(user,owner)
        return auct,200 


@app.route('/myrooms/user',methods=['GET'])
def myauct_u():
    if request.method=='GET':
        user=request.authorization.username
        owner=False
        auct=owned_auctions(user,owner)
        return auct,200 


# Start negotiation: 
# To be done: Verify validity of inputs, for example, x permision for y database is possible

@app.route("/negotiate", methods=['POST'])
def new_neg():

    room_name = request.form.get('room_name')
    bid=request.form.get('price')
    bidder=request.authorization.username
    seller=request.form.get('seller')
    reference_sector=request.form.get('reference_sector')
    reference_type=request.form.get('reference_type')
    quantity=request.form.get('quantity')
    articleno=request.form.get('articleno')
    user=request.authorization.username
    print(user)
    buyersign=get_sign(user)
    sellersign=''
    templatetype=request.form.get('templatetype')
    distance=distance_calc(bidder,seller)
    print('wtf')
    #The following function may be changed to iterate if multiple roles are requested
    room_id=save_room2(room_name,bidder,seller,bidder,sellersign,buyersign,templatetype,bid,distance)
    save_param2(room_id,user,room_name,reference_sector,reference_type,quantity,articleno)
    return {"message":"The negotiation with id {} has been created".format(str(room_id))},200



# This is once the negotiation has been created 

@app.route("/negotiate/<neg_id>", methods=['GET','POST'])

def neg(neg_id):
    user=request.authorization.username
    req=get_neg(neg_id)
    rn=req['payload']['name']['val'][0]
    if request.method == 'POST':
        if user in (req['payload']['seller']['val'][0],req['payload']['created_by']['val'][0]):
            if req['payload']['status']['val'][0] not in ('accepted', 'rejected'):
                bid=request.form.get('bid')
                distance=distance_calc(user,get_room_admin(rn))
                save_message(str(req['_id']),bid,user,get_sign(user),distance)
                change_status(neg_id,1,user,bid)
                return  {"message":"New offer submited for request with id {}".format(str(req['_id']))},200
            else:
                return  {"message":"The negotiation {} has concluded no more offers can be made".format(str(req['_id']))},403
        else:
            return{"message":'You are not part of the current negotiation'}, 403
    elif (request.method=='GET'):
        if req['payload']['status']['val'][0]=='accepted':
            s=sign_contract(neg_id)
            print(s)
            return  {"Contract": "{}".format(s)},200
        else:
            return(neg_info(neg_id)),200


# Only accesible to the owner of such resource, this route accepts the negotiation and begins the contract signing
@app.route("/negotiate/<req_id>/accept", methods=['GET'])

def accept(req_id):
    user=request.authorization.username
    req=get_neg(req_id)
    if user==req['payload']['offer_user']['val'][0]:
        if (user == req['payload']['created_by']['val'][0]) or ((user == req['payload']['seller']['val'][0])):
            flag=change_status(req_id, 'accept',user,0)
            #print(flag)
            ## Add function for contract writing
            if flag: 
                return  {"message":"The negotiation with id {} has been accepted.".format(str(req['_id']))},200
            else:
                return  {"message":"Could not process request, either the accepted auction is already finished or it was declined.".format(str(req['_id']))},200
        else: return {"message":'You are not authorized to perform this task'},403
    else: return {"message":'Wait for the other peer to accept or counter offer'},403



# Only accesible to the owner of such resource, this route cancels the negotiation.
@app.route("/negotiate/<req_id>/cancel", methods=['GET'])

def cancel(req_id):
    req=get_neg(req_id)
    user=request.authorization.username
    if user==req['payload']['offer_user']['val'][0]:
        if (user == req['payload']['created_by']['val'][0]) or ((user == req['payload']['seller']['val'][0])):
            flag=change_status(req_id, 'reject',user,0)
            #print(flag)
            ## Add function for contract writing
            if flag: 
                return  {"message":"The negotiation with id {} has been rejected.".format(str(req['_id']))},200
            else:
                return  {"message":"Could not process request, either the accepted auction is already finished or it was declined.".format(str(req['_id']))},200
        else: return {"message":'You are not authorized to perform this task'},403
    else: return {"message":'You are not allowed to cancel this transaction'},403





@login_manager.user_loader
def load_user(username):
    return get_user(username)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
