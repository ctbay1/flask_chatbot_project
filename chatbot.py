from user_defined import get_part_of_the_day, preprocess_text_v4, colors_list
import pandas as pd
import spacy
import re
from datetime import datetime
from bayes_model import classifier, vectorizer, probability_threshold
import json

responses_df = pd.read_csv('sample_responses.csv')
current_time = datetime.now()

nlp_label_productName_size = spacy.load('./custom_ner_model_5_2')
nlp_label_product_details  = spacy.load('./custom_ner_model_prod_details')

# mock data
sample_data      = pd.read_csv('sample_data.csv')
sample_inventory = pd.read_csv('inventory.csv') 

class ChatBot:

    def __init__(self):
        self.exit_commands   = ("goodbye", "exit")
        self.regexp_patterns = {'regexp_number': r'(\d+)'}
        self.cart = {'items': [], 'order_total': '$0' }
        self.size_map = {
            'xs':['xsmall', 'extra-small', 'extra small'],
            's': ['small'],
            'm': ['medium'],
            'l': ['large'],
            'xl':['xlarge', 'extra-large', 'extra large']
        }
        self.return_window = 14
        self.order_number  = ""
        self.name          = ""
        self.state = {'intent_label':'', 'current_task':''}
        
    def exit_bot(self, user_message):
        for exit_command in self.exit_commands:
            if exit_command in user_message:
                print('Thank you for visiting our [site]! If you have any more questions in the future, feel free to reach out. Have a great day!')
                return True
        return False

    def find_intent(self, responses, user_message):
        processed_transformed_user_message = vectorizer.transform([preprocess_text_v4(user_message)])
        prediction = classifier.predict(processed_transformed_user_message)[0]
        #print(classifier.predict_proba(processed_transformed_user_message)[0])
        if max(classifier.predict_proba(processed_transformed_user_message)[0]) > probability_threshold: #if max probability is greater than threshold (0.2)

            predicted_response     = responses['text'][responses['intent_label'] == prediction].iloc[0]
            predicted_response_idx = responses['index'][responses['intent_label'] == prediction].iloc[0]

            return predicted_response,predicted_response_idx
        
    def find_entities(self, user_message):
        lists_of_entities = [] #final form should be like this -> [[("shirt", "PRODUCT"), ("medium", "SIZE"), ("white", "COLOR")]]

        doc1 = nlp_label_productName_size(user_message.lower())
        num_of_products_mentioned = len([ent.text for ent in doc1.ents if ent.label_ == "PRODUCT"])
        
        if num_of_products_mentioned > 1:
            doc2 = nlp_label_product_details(user_message.lower())
            product_details_list = [ent.text for ent in doc2.ents]
            for product_detail in product_details_list:
                doc1_2 = nlp_label_productName_size(product_detail)
                product_info_list = [(ent.text, ent.label_) for ent in doc1_2.ents]
                product_info_list.append([(word.text, 'COLOR') for word in doc1_2 if word.text in colors_list][0])
                lists_of_entities.append(product_info_list)
            return lists_of_entities
        else:
            try:
                product_info_list = []
                product_info_list = [(ent.text, ent.label_) for ent in doc1.ents]
                product_info_list.append([(word.text, 'COLOR') for word in doc1 if word.text in colors_list][0])
                lists_of_entities.append(product_info_list)
            except:
                lists_of_entities.append(product_info_list)
            return lists_of_entities
    
    def get_size_product_color_from_extracted_entities(self, list_of_entities):
        mentioned_product, mentioned_size, mentioned_color = '','',''
        for entity in list_of_entities:
            if entity[1] == "COLOR":
                mentioned_color = entity[0]
            
            elif entity[1] == "SIZE":
                for key, value_list in self.size_map.items():
                    for value in value_list:
                        if value == entity[0] or key == entity[0]:
                            mentioned_size = key
                size_numbers_match = re.findall(self.regexp_patterns['regexp_number'], entity[0]) #if size information includes numbers such as waist size 34
                if size_numbers_match:
                    mentioned_size = 'w' + size_numbers_match[0]
                    if len(size_numbers_match) == 2:
                        mentioned_size += ('l' + size_numbers_match[1])

            elif entity[1] == "PRODUCT":
                if entity[0] in sample_inventory['name'].unique(): #if the plural form exists in the inventory, get that
                    mentioned_product = entity[0]
                else:
                    mentioned_product = preprocess_text_v4(entity[0]) #if not, preprocess to make it singular: shirts -> shirt
        
        return mentioned_product, mentioned_size, mentioned_color
    
    def get_cart_order_total(self, data_type, item_price, purchased_quantity, current_order_total):
        if data_type == 'df':
            item_price = float(item_price.iloc[0][1:])
        else: # might add conditions later for different data types
            item_price = float(item_price[1:])
        current_order_total = float(current_order_total[1:])

        calculated_new_order_total = round(((item_price * purchased_quantity) + current_order_total), 2)
        return '$' + str(calculated_new_order_total)

    def get_whole_cart_order_total(self, cart_items):
        total = 0
        if cart_items:
            for product in cart_items:
                total += float(product['price'][1:]) * int(product['purchased_quantity'])
        return '$' + str(round(total, 2))
    
    def is_product_with_size_and_color_in_inventory(self, inventory_category, product_name, product_size, product_color):
        try:
            product_info = sample_inventory[inventory_category][(sample_inventory['name'] == product_name) & 
                            (sample_inventory['color'] == product_color) & (sample_inventory['size'] == product_size)].iloc[0]
        except:
            product_info = False
        return product_info

    def handle_stock_info(self, mentioned_product, mentioned_color, mentioned_size):
        available_flag = False
        is_mentioned_product_sold = mentioned_product in sample_inventory['name'].unique()
        if is_mentioned_product_sold:
            product_color_size_in_stock_quantity = self.is_product_with_size_and_color_in_inventory("stock_quantity", mentioned_product, mentioned_size, mentioned_color)
            if product_color_size_in_stock_quantity and product_color_size_in_stock_quantity > 0:
                available_flag = True
                url = "https://ctbay.pythonanywhere.com/product/{product_name}/{product_size}_and_{product_color}".format(
                    product_name=mentioned_product, product_size=mentioned_size, product_color=mentioned_color)
                return("Great news! We have a {color} {clothing} in {size} available. You can check it out here: [{url}]."
                        .format(color=mentioned_color, clothing=mentioned_product, size=mentioned_size, url=url)),available_flag
            else:
                list_of_available_sizes_for_mentioned_product  = sample_inventory[sample_inventory['name'] == mentioned_product]['size'].to_list()
                list_of_available_colors_for_mentioned_product = sample_inventory[sample_inventory['name'] == mentioned_product]['color'].to_list()
                list_of_available_size_and_color_pairs_for_mentioned_product = list(zip(list_of_available_sizes_for_mentioned_product, list_of_available_colors_for_mentioned_product))
                url = "https://ctbay.pythonanywhere.com/product/{product_name}".format(product_name=mentioned_product)
                if mentioned_color and mentioned_size:
                    return("I'm sorry to inform you that we don't have a {color} {clothing} in {size} available at the moment. "
                        "However, we do have {clothing}(s) in the following size and color pairs: {list_of_available_sizes}. "
                        "Would you like to see those options instead? Here's the link: [{url}]."
                        .format(color=mentioned_color, clothing=mentioned_product, size=mentioned_size, 
                        list_of_available_sizes=list_of_available_size_and_color_pairs_for_mentioned_product,url=url)),available_flag
                else:
                    return("We do have {clothing}(s) in the following size and color pairs: {list_of_available_sizes}. "
                        "Would you like to see them? Here's the link: [{url}]."
                        .format(clothing=mentioned_product, list_of_available_sizes=list_of_available_size_and_color_pairs_for_mentioned_product,url=url)),available_flag
        else:
            if mentioned_product:
                return("Thank you for your inquiry! We don't sell {requested_item}, is there anything else I can help you find today?"
                   .format(requested_item=mentioned_product)),available_flag
            else:
                return("Thank you for your inquiry! We don't sell that item, is there anything else I can help you find today?")
    
    def handle_order_status(self, order_number):
        sample_data_lst = sample_data['order_number'].to_list()
        for order_num in sample_data_lst:
            if str(order_num) == order_number:
                idx    = sample_data_lst.index(order_num)
                status = sample_data['status'].iloc[idx]
                items  = sample_data['items'].iloc[idx]
                if status == 'shipped':
                    return ("Hey! I just checked my records, your shipment containing [{items}] is en route. Expect it to be delivered within the next two days!"
                            .format(items=items))
                elif status == 'processing':
                    return ("Hey! I just checked my records, your shipment containing [{items}] is currently processing. Expected to be shipped in two days."
                            .format(items=items))
        return input('We were unable to locate an order associated with the provided number. Could you please double-check the order number and try again?')
    
    def handle_refund(self, order_number):
        sample_data_lst = sample_data['order_number'].to_list()
        for order_num in sample_data_lst:
            if str(order_num) == order_number:
                idx    = sample_data_lst.index(order_num)
                status = sample_data['status'].iloc[idx]
                items  = sample_data['items'].iloc[idx]
                if status == 'processing':
                    # update inventory
                    for item in items.split(','):
                        item_lst = item.split()
                        item_color = item_lst[0]
                        item_name  = item_lst[1]
                        item_size  = item_lst[2]
                        stock_quantity = sample_inventory['stock_quantity'][(sample_inventory['name'] == item_name) & 
                        (sample_inventory['color'] == item_color) & (sample_inventory['size'] == item_size)].iloc[0]
                        stock_quantity += 1
                        inv_idx = sample_inventory['index'][(sample_inventory['name'] == item_name) & 
                        (sample_inventory['color'] == item_color) & (sample_inventory['size'] == item_size)].iloc[0]
                        sample_inventory.at[inv_idx, 'stock_quantity'] = stock_quantity

                    sample_data.at[idx, 'status'] = 'cancelled'
                    
                    sample_inventory.to_csv('inventory.csv', index=False)
                    sample_data.to_csv('sample_data.csv', index=False)
                    return ("We've successfully cancelled your order containing [{items}]. " 
                            "Your refund is being processed, and you can expect the funds to be transferred back to your account within 3 business days. "
                            "If you have any further questions or concerns, please don't hesitate to reach out to us. We're here to assist you every step of the way."
                            .format(items=items))
                
                elif status == 'shipped':
                    return ("Since your order has already been shipped, we kindly ask for your patience as it makes its way to you. "
                            "Once you receive the order, if there are any issues or concerns, such as the need for a return or exchange, "
                            "please don't hesitate to contact us for assistance.")
                elif status == 'delivered':
                    return ("As your order has already been delivered, we hope everything arrived to your satisfaction. "
                            "If you're considering a return or exchange for any reason, please reach out to us and we'll be happy to guide you through the process. "
                            "Your satisfaction is our priority.")
    
    def handle_return(self, order_number):
        sample_data_lst = sample_data['order_number'].to_list()
        for order_num in sample_data_lst:
            if str(order_num) == order_number:
                idx    = sample_data_lst.index(order_num)
                status = sample_data['status'].iloc[idx]
                items  = sample_data['items'].iloc[idx]
                delivery_date = sample_data['delivery_date'].iloc[idx]
                del_date_obj  = datetime.strptime(delivery_date, "%Y-%m-%d")
                days_passed_since_delv = (del_date_obj - current_time).days 
                if status == 'delivered':
                    if days_passed_since_delv <= self.return_window:
                    # update inventory
                        for item in items.split(','):
                            item_lst = item.split()
                            item_color = item_lst[0]
                            item_name = item_lst[1]
                            item_size = item_lst[2]
                            stock_quantity = sample_inventory['stock_quantity'][(sample_inventory['name'] == item_name) & 
                            (sample_inventory['color'] == item_color) & (sample_inventory['size'] == item_size)].iloc[0]
                            stock_quantity += 1
                            inv_idx = sample_inventory['index'][(sample_inventory['name'] == item_name) & 
                            (sample_inventory['color'] == item_color) & (sample_inventory['size'] == item_size)].iloc[0]
                            sample_inventory.at[inv_idx, 'stock_quantity'] = stock_quantity
                        
                        sample_data.at[idx, 'status'] = 'cancelled'
                        
                        sample_inventory.to_csv('inventory.csv', index=False)
                        sample_data.to_csv('sample_data.csv', index=False)
                        return ("We've successfully processed your return for the {items}. " 
                                "Your refund is being initiated, and you can expect the funds to be transferred back to your account within 3 business days. "
                                "If you have any further questions or concerns, please don't hesitate to reach out to us. We're here to assist you every step of the way."
                                .format(items=items))
                    else:
                        return ("We apologize, but it seems it's been more than 14 days since your package was delivered. "
                                "Unfortunately, our return window has expired, and we're unable to process a return for your order."
                                "If you have any further questions or concerns, please feel free to contact us. We're here to assist you in any way we can.")
                
                elif status == 'shipped':
                    return ("Since your order has already been shipped, we kindly ask for your patience as it makes its way to you. "
                            "Once you receive the order, if there are any issues or concerns, such as the need for a return or exchange, "
                            "please don't hesitate to contact us for assistance.")
                elif status == 'processing':
                    return ("We see that your order is currently in the processing stage. "
                            "If you're considering returning your order, we recommend cancelling it instead since it hasn't been shipped yet. "
                            "Cancelling now will prevent any inconvenience caused by returning the order after it's been shipped. "
                            "Would you like to proceed with cancelling your order?")

    def handle_package_issues(self, order_number):
        print("We strive to ensure that our customers receive their orders in perfect condition. "
              "If any item in your order is found to be damaged or unavailable, we offer a solution tailored to your needs. "
              "If the item is currently in stock, we're pleased to offer a replacement to ensure your complete satisfaction. "
              "However, if the item is no longer available, rest assured that we'll process a full refund for you promptly. "
              "Your satisfaction is our priority, and we're here to assist you every step of the way.")
        
        sample_data_lst = sample_data['order_number'].to_list()
        for order_num in sample_data_lst:
            if str(order_num) == order_number:
                idx    = sample_data_lst.index(order_num)
                status = sample_data['status'].iloc[idx]
                items  = sample_data['items'].iloc[idx]
                delivery_date = sample_data['delivery_date'].iloc[idx]
                del_date_obj  = datetime.strptime(delivery_date, "%Y-%m-%d")
                days_passed_since_delv = (del_date_obj - current_time).days 
                if status == 'delivered':
                    if days_passed_since_delv <= self.return_window:
                    # update inventory
                        items2replace = []
                        items2refund  = []
                        items_price   = 0
                        for item in items.split(','):
                            item_lst = item.split()
                            item_color = item_lst[0]
                            item_name = item_lst[1]
                            item_size = item_lst[2]
                            stock_quantity = sample_inventory['stock_quantity'][(sample_inventory['name'] == item_name) & 
                            (sample_inventory['color'] == item_color) & (sample_inventory['size'] == item_size)].iloc[0]
                            if stock_quantity > 0:
                                items2replace.append(item)
                                item_price = float(sample_inventory['price'][(sample_inventory['name'] == item_name) & 
                                (sample_inventory['color'] == item_color) & (sample_inventory['size'] == item_size)].iloc[0][1:])
                                items_price += item_price

                                inv_idx = sample_inventory['index'][(sample_inventory['name'] == item_name) & 
                                (sample_inventory['color'] == item_color) & (sample_inventory['size'] == item_size)].iloc[0]
                                stock_quantity -= 1
                                sample_inventory.at[inv_idx, 'stock_quantity'] = stock_quantity
                            else:
                                items2refund.append(item)
                                print("Unfortunately, the item you ordered is no longer available in our inventory for a replacement. "
                                      "However, we can offer you a full refund instead. Initiating your refund process now...")

                        if len(items2replace) > 0:
                            print("We've confirmed that the {items} you ordered is still in stock. We'll be sending you a replacement promptly."
                                  .format(items=items2replace))
                            new_row_dict = sample_data.iloc[idx].to_dict()
                            new_row_dict['index'] += len(sample_data)
                            new_row_dict['order_number'] += 1
                            new_row_dict['status']      = 'processing'
                            new_row_dict['items']       = ','.join(items2replace)
                            new_row_dict['order_total'] = items_price
                            new_row_dict['order_date']  = datetime.strftime(current_time, "%Y-%m-%d")
                            new_row_df  = pd.DataFrame(new_row_dict, index=[0])
                            sample_data = pd.concat([sample_data, new_row_df], ignore_index=True)
                            print("We've placed a new order for you with the order number {order_number}. "
                                  "Your replacement item will be shipped out within approximately 2 days. Thank you for your understanding and patience."
                                  .format(order_number=new_row_dict['order_number']))
                        if len(items2refund) > 0:
                            print("Unfortunately, the {items} you ordered is no longer available in our inventory for a replacement. "
                                "However, we can offer you a full refund instead. Initiating your refund process now...".format(items=items2replace))
                            sample_data.at[idx, 'status'] = 'cancelled'
                            sample_data.at[idx, 'items']  = ','.join(items2replace)
                        
                        sample_inventory.to_csv('inventory.csv', index=False)
                        sample_data.to_csv('sample_data.csv', index=False)        
                        return ("If you have any further questions or concerns, please don't hesitate to reach out to us. We're here to assist you every step of the way.")
                    else:
                        return ("We apologize, but it seems it's been more than 14 days since your package was delivered. "
                                "Unfortunately, our return window has expired, and we're unable to address the issue with your order at this time."
                                "If you have any further questions or concerns, please feel free to contact us. We're here to assist you in any way we can.")
                
                elif status == 'shipped':
                    return ("Since your order has already been shipped, we kindly ask for your patience as it makes its way to you. "
                            "Once you receive the order, if there are any issues or concerns, such as the need for a return or exchange, "
                            "please don't hesitate to contact us for assistance.")
                elif status == 'processing':
                    return ("We see that your order is currently in the processing stage. "
                            "If you're considering returning your order, we recommend cancelling it instead since it hasn't been shipped yet. "
                            "Cancelling now will prevent any inconvenience caused by returning the order after it's been shipped. "
                            "Would you like to proceed with cancelling your order?")

    def handle_cart(self, mentioned_product, mentioned_size, mentioned_color):

        mentioned_product_in_inventory = sample_inventory[(sample_inventory['name'] == mentioned_product) & 
        (sample_inventory['size'] == mentioned_size) & (sample_inventory['color'] == mentioned_color)].to_dict('records')[0]
        mentioned_product_in_inventory['purchased_quantity'] = 1
        mentioned_product_in_inventory['cart_index'] = len(self.cart['items'])

        self.cart['items'].append(mentioned_product_in_inventory)
        self.cart['order_total'] = self.get_whole_cart_order_total(self.cart['items'])
        return ("Your {size} sized {color} {clothing} has been successfully added to your cart. You can proceed to checkout to complete your purchase."
                .format(size=mentioned_size,color=mentioned_color,clothing=mentioned_product))
    
    def directing_function(self, user_message, best_response, response_intent):

        if response_intent == 'navigation':
            best_response = "This functionality is still work in progress."

        elif response_intent == 'add_cart':
            lists_of_entities = self.find_entities(user_message=user_message)
            for list_of_entities in lists_of_entities:
                mentioned_product, mentioned_size, mentioned_color = self.get_size_product_color_from_extracted_entities(list_of_entities)
                best_response, is_available = self.handle_stock_info(mentioned_product=mentioned_product, mentioned_size=mentioned_size, mentioned_color=mentioned_color)
                if is_available:
                    best_response = self.handle_cart(mentioned_product=mentioned_product, mentioned_size=mentioned_size, mentioned_color=mentioned_color)

        elif response_intent == 'stock_info':
            lists_of_entities = self.find_entities(user_message=user_message)
            for list_of_entities in lists_of_entities:
                mentioned_product, mentioned_size, mentioned_color = self.get_size_product_color_from_extracted_entities(list_of_entities)
                best_response = self.handle_stock_info(mentioned_product=mentioned_product, mentioned_size=mentioned_size, mentioned_color=mentioned_color)[0]

        elif response_intent == 'order_status':
            if self.order_number:
                best_response = self.handle_order_status(self.order_number)
            else:
                order_number_match = re.search(self.regexp_patterns['regexp_number'], user_message)
                if order_number_match:
                    self.order_number = order_number_match.groups()[0]
                    best_response = self.handle_order_status(self.order_number)
                else:
                    self.state['current_task'] = "waiting for an input"
                    self.state['intent_label'] = 'order_status'
                    best_response = "To track your order, please provide your order number and we'll be happy to retrieve the status for you."

        elif response_intent == 'refunds':
            if self.order_number:
                best_response = self.handle_refund(self.order_number)
            else:
                order_number_match = re.search(self.regexp_patterns['regexp_number'], user_message)
                if order_number_match:
                    self.order_number = order_number_match.groups()[0]
                    best_response = self.handle_refund(self.order_number)
                else:
                    self.state['current_task'] = "waiting for an input"
                    self.state['intent_label'] = 'refunds'
                    best_response = "To assist you with your refund request, could you please provide your order number about your recent purchase?"

        elif response_intent == 'returns':
            best_response = "This functionality is still work in progress."

        elif response_intent == 'package_issues':
            best_response = "This functionality is still work in progress."

        else:
            best_response = best_response

        return best_response

    def respond(self, user_message):
        try:
            if self.state['intent_label'] and self.state['current_task']:
                best_response = self.directing_function(user_message, "", self.state['intent_label'])
                self.state['current_task'] = ''
            else:
                best_response, best_response_idx = self.find_intent(responses_df, user_message)
                best_response_intent_label = responses_df['intent_label'].iloc[best_response_idx]
                best_response = self.directing_function(user_message, best_response, best_response_intent_label)
        except:
            best_response = "I'm sorry, I didn't quite understand that. Could you rephrase your question?"
        return json.dumps({'response':best_response})
        #return input(best_response + "\n") commented out this line to make it suitable to a web application

    # chat
    def chat(self):
        user_message = input("{greeting_day} Welcome to [website name]! I'm an automated assistant designed to provide support and guidance.\n"
        "To end the conversation, you can simply type 'exit' or 'goodbye'.\n"
        .format(greeting_day=get_part_of_the_day(current_time)))
        while self.exit_bot(user_message) == False:
            user_message = self.respond(user_message)
    
#chatbot = ChatBot()
#chatbot.chat()