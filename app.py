from flask import Flask, render_template, request, redirect, url_for, session, g
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired
from chatbot import ChatBot
from user_defined import get_part_of_the_day
from datetime import datetime
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash

products_df   = pd.read_csv('inventory.csv')
product_types = list(products_df['name'].unique())
products      = products_df.to_dict('records')
    
app = Flask(__name__)
app.config["SECRET_KEY"] = "mysecret"
app.config['SESSION_TYPE'] = 'filesystem'
chatbot = ChatBot()

@app.before_request
def before_request():
    if 'username_for_route' not in session:
        session['username_for_route'] = ""
    if 'user_logged_in' not in session:
        session['user_logged_in'] = False
    if 'hidden_username_error' not in session:
        session['hidden_username_error'] = "hidden"
    if 'hidden_password_error' not in session:
        session['hidden_password_error'] = "hidden"

class ChatbotForm(FlaskForm):
    message = StringField("Message", validators=[DataRequired()])
    send    = SubmitField("Send")

class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    login    = SubmitField("Login")

@app.route('/', methods=["GET", "POST"])
def index():
    greeting_day  = get_part_of_the_day(datetime.now())
    
    chatbot_form = ChatbotForm()
    if chatbot_form.validate_on_submit():
        new_response = chatbot.respond(chatbot_form.message.data)
        return new_response  # Return the JSON response for JavaScript to handle
    # Render the template for GET requests or when the form fails validation
    return render_template('index.html', 
                           product_types=product_types, 
                           template_form=chatbot_form, 
                           greeting_day=greeting_day, 
                           products=products, 
                           username=session['username_for_route']
                           )

@app.route('/product/<product_type>')
def category(product_type):
    greeting_day = get_part_of_the_day(datetime.now())
    
    the_same_type_of_products = products_df[products_df['name'] == product_type].to_dict('records')

    chatbot_form = ChatbotForm()
    if chatbot_form.validate_on_submit():
        new_response = chatbot.respond(chatbot_form.message.data)
        return new_response
    
    return render_template('index.html', 
                           product_types=product_types, 
                           template_form=chatbot_form, 
                           greeting_day=greeting_day, 
                           products=the_same_type_of_products, 
                           username=session['username_for_route']
                           )

@app.route('/product/<product_type>/<productSize_and_color>', methods=["GET", "POST"])
def product_page(product_type, productSize_and_color):
    greeting_day = get_part_of_the_day(datetime.now())
    
    size, color  = productSize_and_color.split('_and_')

    product  = products_df[(products_df['name'] == product_type) & (products_df['size'] == size) & (products_df['color'] == color)]
    product  = product.to_dict('records')[0]

    chatbot_form = ChatbotForm()
    if chatbot_form.validate_on_submit():
        new_response = chatbot.respond(chatbot_form.message.data)
        return new_response
    
    if request.method == "POST":
        if request.form['add_to_cart_button'] == "Add to Cart":
            product['purchased_quantity'] = 1
            product['cart_index'] = len(chatbot.cart['items'])
            chatbot.cart['items'].append(product)
            chatbot.cart['order_total'] = chatbot.get_cart_order_total(data_type='dict', item_price=product['price'], 
            purchased_quantity=product['purchased_quantity'], current_order_total=chatbot.cart['order_total'] )
            return redirect(url_for('product_page', product_type=product_type, productSize_and_color=productSize_and_color))

    return render_template('product_page.html', 
                           product_types=product_types, 
                           template_form=chatbot_form, 
                           greeting_day=greeting_day, 
                           product=product, 
                           username=session['username_for_route']
                           )

@app.route('/cart', methods=["GET", "POST"])
def cart():
    greeting_day = get_part_of_the_day(datetime.now())
    
    chatbot_form = ChatbotForm()
    if chatbot_form.validate_on_submit():
        new_response = chatbot.respond(chatbot_form.message.data)
        return new_response
    
    if request.method == "POST":
        text_list = request.form['quantity_selector'].strip('[').strip(']').split(',')
        updated_quantity   = int(text_list[0])
        item_index_in_cart = int(text_list[1])
        for product in chatbot.cart['items']:
            if product['cart_index'] == item_index_in_cart:
                item_index_in_cart = chatbot.cart['items'].index(product)
        if updated_quantity == 0:
            chatbot.cart['items'].pop(item_index_in_cart)
            chatbot.cart['order_total'] = chatbot.get_whole_cart_order_total(chatbot.cart['items'])
            return redirect(url_for('cart'))
        else:
            chatbot.cart['items'][item_index_in_cart]['purchased_quantity'] = updated_quantity
            chatbot.cart['order_total'] = chatbot.get_whole_cart_order_total(chatbot.cart['items'])
            return redirect(url_for('cart'))
    
    return render_template('cart_page.html', 
                           product_types=product_types, 
                           template_form=chatbot_form, 
                           greeting_day=greeting_day, 
                           cart=chatbot.cart, 
                           username=session['username_for_route']
                           )

@app.route('/login', methods=["GET", "POST"])
def login():
    
    

    greeting_day     = get_part_of_the_day(datetime.now())

    registered_users = pd.read_csv('sample_users.csv') 
    
    chatbot_form = ChatbotForm()
    if chatbot_form.validate_on_submit():
        new_response = chatbot.respond(chatbot_form.message.data)
        return new_response

    def check_if_entered_username_exists(entered_username, registered_usernames_list):
        for username in registered_usernames_list:
            if username == entered_username:
                return True, registered_usernames_list.index(username)
        return False, 0

    login_form = LoginForm()
    if login_form.validate_on_submit():
        entered_username = login_form.username.data
        entered_password = login_form.password.data
        entered_username_found, entered_username_index_in_data = check_if_entered_username_exists(entered_username=entered_username, registered_usernames_list=registered_users['username'].to_list())
        if entered_username_found:
            if check_password_hash(registered_users['password_hash'].iloc[entered_username_index_in_data], entered_password):
                session['username_for_route'] = entered_username
                session['user_logged_in']     = True

                session['hidden_username_error'] = "hidden"
                session['hidden_password_error'] = "hidden"
                return redirect(url_for('profile', username=session['username_for_route']))
            else:
                session['hidden_username_error'] = "hidden"
                session['hidden_password_error'] = ""
                return redirect(url_for('login'))
        else:
            session['hidden_password_error'] = "hidden"
            session['hidden_username_error'] = ""
            return redirect(url_for('login'))
    
    return render_template('login_page.html', 
                           product_types=product_types, 
                           template_form=chatbot_form, 
                           greeting_day=greeting_day,
                           username=session['username_for_route'], 
                           login_form=login_form,
                           username_not_found=session['hidden_username_error'],
                           incorrect_password=session['hidden_password_error']
                           )

@app.route('/profile/<username>', methods=["GET", "POST"])
def profile(username):
    if not session['user_logged_in']:
        return redirect(url_for('login'))
    
    greeting_day = get_part_of_the_day(datetime.now())

    registered_users = pd.read_csv('sample_users.csv')
    orders_data      = pd.read_csv('sample_data.csv')

    user_data                        = registered_users[registered_users['username'] == username].to_dict('records')[0]
    user_idx_in_user_data            = registered_users['index'][registered_users['username'] == username].iloc[0]
    orders_data_filtered_by_username = orders_data[orders_data['username'] == username].to_dict('records')
    user_data['latest_order_number'] = orders_data_filtered_by_username[-1]['order_number']
    registered_users.at[user_idx_in_user_data, 'latest_order_number'] = user_data['latest_order_number']
    chatbot.order_number = str(user_data['latest_order_number'])
    print(chatbot.order_number)
    user_data['products_ordered'] = {}
    for order in orders_data_filtered_by_username:
        user_data['products_ordered'][str(order['index'])] = []
        for product_str in order['items'].split(','):
            product_lst      = product_str.split()
            product_ordered  = products_df[(products_df['name'] == product_lst[1]) & (products_df['size'] == product_lst[2]) & (products_df['color'] == product_lst[0])]
            product_ordered  = product_ordered.to_dict('records')[0]
            product_ordered['purchased_quantity'] = int(product_lst[3][1:])
            product_ordered['order_number'] = order['order_number']
            product_ordered['status'] = order['status']
            product_ordered['order_total'] = order['order_total']
            product_ordered['order_date'] = order['order_date']
            product_ordered['delivery_date'] = order['delivery_date']
            user_data['products_ordered'][str(order['index'])].append(product_ordered)
        
    chatbot_form = ChatbotForm()
    if chatbot_form.validate_on_submit():
        new_response = chatbot.respond(chatbot_form.message.data)
        return new_response

    registered_users.to_csv('sample_users.csv', index=False)

    if request.method == "POST":
        if request.form['log_out'] == 'LogOut':
            session['user_logged_in']     = False
            session['username_for_route'] = ''
            return redirect(url_for('login'))

    return render_template('profile_page.html', 
                           product_types=product_types, 
                           template_form=chatbot_form, 
                           greeting_day=greeting_day,
                           username=session['username_for_route'],
                           user_data=user_data 
                           )
