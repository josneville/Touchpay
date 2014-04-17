import os
from flask import Flask, render_template, request, g
import stripe
import json
import psycopg2

conn = psycopg2.connect(
    database="Nope. Not giving you this",
    user="I'm not giving you my username",
    password="Or my password",
    host="ec2-54-204-2-217.compute-1.amazonaws.com",
    port=5432
)
app = Flask(__name__)
stripe.api_key = "sk_test_setJmneBfstSvHSULFKvh6Xs" #<-- Expired
@app.route('/')
def hello():
    return render_template('base.html')

@app.route('/interested', methods=['POST', 'GET'])
def interested_handler():
    if 'email' in request.form and str(request.form['email']) != "":
	email = str(request.form['email'])
    else:
	return render_template('base.html')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO interested VALUES (%s)", (email,))
    conn.commit()
    return "Thank You! Your e-mail has been recorded and you will receive updates on our progress!"

@app.route('/createCCToken', methods=['POST', 'GET'])
def createCCToken_handler():
    if 'number' in request.form and 'exp_month' in request.form and 'exp_year' in request.form and 'cvc' in request.form:
	number = str(request.form['number'])
	exp_month = int(request.form['exp_month'])
	exp_year = int(request.form['exp_year'])
	cvc = str(request.form['cvc'])
    else:
	return "Not Enough Information", 201
    try:
	token = stripe.Token.create(
  		card={
    			"number": number,
    			"exp_month": exp_month,
    			"exp_year": exp_year,
    			"cvc": cvc
  		},
	)
	return token.id, 200
    except:
	return "Fail for Unknown Reasons", 205

@app.route('/createBankToken', methods=['POST', 'GET'])
def createBankToken_handler():
    if 'country' in request.form and 'routing_number' in request.form and 'account_number' in request.form:
		country = str(request.form['country'])
		routing_number = str(request.form['routing_number'])
		account_number = str(request.form['account_number'])
    else:
		return "Not Enough Information", 201
    try:
	token = stripe.Token.create(
  		bank_account={
    			"country":country,
    			"routing_number": routing_number,
    			"account_number": account_number
  		},
	)
	return token.id, 200
    except:
	return "Fail for Unknown Reasons", 205

@app.route('/createUser', methods=['POST','GET'])
def createUser_handler():
    if 'token_id' in request.form and 'bank_id' in request.form and 'name' in request.form and 'email' in request.form and 'password' in request.form:
	token = str(request.form['token_id'])
        bankToken = str(request.form['bank_id'])
	rcName = str(request.form['name'])
	rcEmail = str(request.form['email'])
	password = str(request.form['password'])
    else:
	return "Not Enough Information", 201
    try:
	customer = stripe.Customer.create(
    		card=token,
		email=rcEmail,
		description=rcName		
	)
	recipient = stripe.Recipient.create(
  		name=rcName,
  		type="individual",
  		email=rcEmail,
  		bank_account=bankToken
	)
    except stripe.CardError, e:
	message = str(e)
        return render_template('chargetest.html', error_message=str(message)), 202
    except stripe.InvalidRequestError, e:
        message = str(e)
        return render_template('chargetest.html', error_message=str(message)), 205
    cursor = conn.cursor()
    cursor.execute("INSERT INTO userData VALUES (%s, %s, %s, %s, %s)", (rcName, rcEmail, password, customer.id, recipient.id))
    cursor.execute("INSERT INTO accountBalance VALUES (%s, %s)", (customer.id, 0))
    conn.commit()
    return customer.id, 200  
 
@app.route('/charge', methods=['POST', 'GET'])
def charge_handler():
    if 'senderEmail' in request.form and 'cents' in request.form and 'receiverEmail' in request.form:
        senderEmail = str(request.form['senderEmail'])
        cents = int(request.form['cents'])
 	receiverEmail = str(request.form['receiverEmail'])
    else:
        return "Not enough information", 201
    amountCharged = cents * 1.025
    cursor = conn.cursor()
    cursor.execute("SELECT customer_id FROM userData WHERE email = %s", (senderEmail,))
    customerToken = cursor.fetchone()[0]
    cursor.execute("SELECT customer_id FROM userData WHERE email = %s", (receiverEmail,))
    receiverToken = cursor.fetchone()[0]
    try:
        charge = stripe.Charge.create(
 		amount=int(amountCharged),
  		currency="usd",
		customer=customerToken
	)
    except stripe.CardError, e:
        message = str(e)
        return render_template('chargetest.html', error_message=str(message)), 203
    except:
        return render_template('chargetest.html', error_message="Unknown Error"), 205
    cursor = conn.cursor()
    cursor.execute("INSERT INTO transactionHistory VALUES (%s, %s, %s)", (receiverToken, customerToken, cents))
    cursor.execute("UPDATE accountBalance SET balance = balance + %s WHERE customer_id = %s", (cents, receiverToken,)) 
    conn.commit()
    return "Success", 200
 
@app.route('/transfer', methods=['POST','GET'])
def transfer_handler():
    if 'receiverEmail' in request.form:
		receiverEmail = str(request.form['receiverEmail'])
    else:
	return "Recipient not found", 201
    cursor = conn.cursor()
    cursor.execute("SELECT customer_id FROM userData WHERE email = %s", (receiverEmail,))
    customerToken = cursor.fetchone()[0]
    cursor.execute("SELECT balance FROM accountBalance WHERE customer_id = %s", (customerToken,))
    accountBalance = cursor.fetchone()
    balance = int(accountBalance[0] * 0.975)
    cursor.execute("SELECT recipient_id FROM userData WHERE customer_id = %s", (customerToken,))
    userDataRow = cursor.fetchone()
    recipient = userDataRow[0]
    try:
    	stripe.Transfer.create(
    		amount=balance,
    		currency="usd",
    		recipient=recipient,
    		description="Transfer for test@example.com"
    	)
    except:
	return "Fail", 205
    cursor.execute("UPDATE accountBalance SET balance = 0 WHERE customer_id = %s", (customerToken,))
    conn.commit()
    return "Success", 200

@app.route('/login', methods=['POST', 'GET'])
def login_handler():
    if 'email' in request.form and 'password' in request.form:
	email = str(request.form['email'])
        password = str(request.form['password'])
    else:
		return "Not enough information", 250
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM userData WHERE email = %s AND password = %s", (email, password,))
    loginData = cursor.fetchone()
    if loginData is None: 
		return "Username and Password does not match or exit", 245 
    return str(loginData[3]), 200  

