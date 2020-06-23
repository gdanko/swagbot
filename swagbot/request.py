import swagbot.exception as exception
import swagbot.utils as utils
import inspect
import json
import os
import re
import requests
import sys
from urllib.parse import urlencode

def get(client, uri=None, qs=None, payload=None, proxy=None, extra_headers=None):
	__swagbot_request(client, http_method="GET", uri=uri, qs=qs, payload=payload, proxy=proxy, extra_headers=extra_headers)

def post(client, uri=None, qs=None, payload=None, proxy=None, extra_headers=None):
	__swagbot_request(client, http_method="POST", uri=uri, qs=qs, payload=payload, proxy=proxy, extra_headers=extra_headers)

def put(client, uri=None, qs=None, payload=None, proxy=None, extra_headers=None):
	__swagbot_request(client, http_method="PUT", uri=uri, qs=qs, payload=payload, proxy=proxy, extra_headers=extra_headers)

def delete(client, uri=None, qs=None, payload=None, proxy=None, extra_headers=None):
	__swagbot_request(client, http_method="DELETE", uri=uri, qs=qs, payload=payload, proxy=proxy, extra_headers=extra_headers)

def __get_method(stack):
	valid_scripts = ["auth.py", "core.py"]
	usable_bits = [frame for frame in stack if os.path.basename(frame[1]) in valid_scripts]
	return usable_bits[-1][3] if len(usable_bits) > 0 else "unknown method"

def __swagbot_request(client, http_method=None, uri=None, qs=None, payload=None, proxy=None, extra_headers=None):
	method = __get_method(inspect.stack())
	url = None
	req = None
	res = None
	body = None
	json_body = None
	client.logger.debug("Executing method: {0}".format(method))
	headers = {}
	errors, message = [],[]


	headers["Content-Type"] = "application/json"
	if extra_headers:
		for k, v in extra_headers.items():
			headers[k] = v

	if qs and isinstance(qs, dict):
		if len(qs.keys()) > 0:
			qs_arr = []
			for k in qs.keys():
				qs_arr.append( urlencode({k: str(qs[k])}) )
			qs_str = "&".join(qs_arr)
			url = "{0}?{1}".format(uri, qs_str)
		else:
			url = uri
	else:
		url=uri

	client.logger.debug("{0} {1}".format(http_method, url))
	if payload:
		if not "api_signature" in payload:
			client.logger.debug("payload: {0}".format(payload))

	#if binary_body:
	#	client.logger.debug("binary body: {0}".format(binary_body))

	if payload:
		res = requests.request(http_method, url, proxies=proxy, headers=headers, data=json.dumps(payload))
	else:
		res = requests.request(http_method, url, proxies=proxy, headers=headers)

	# HTML body
	body = res.text
	if len(body) <= 0: body = ""

	# Content-length
	if res.headers.get("content-length"):
		content_length = int(res.headers.get("content-length"))
	else:
		content_length = len(body) if len(body) > 0 else 0

	# JSON body
	try:
		if isinstance(body, str):
			json_body = utils.validate_json(body)
		elif isinstance(body, bytes):
			json_body = utils.validate_json(body.decode("utf-8"))
	except:
		json_body = None

	# Other stuff
	status_code = res.status_code
	content_type = res.headers.get("content-type")
	client.response = {}

	if content_length > 0:
		if "application/json" in content_type:
			if isinstance(json_body, dict):
				client.response = json_body
			elif isinstance(json_body, list):
				client.response = {"body": json_body}
		elif "text/html" in content_type:
			client.success = False
			client.response = {"body": body}

	client.response["status_code"] = status_code


	if (status_code >= 200) and (status_code < 400):
		client.response["success"] = True
		if content_length <= 0:
			client.response["body"] = "The method {0} completed successfully".format(method)
	else:
		client.response["success"] = False
		if content_length <= 0:
			client.response["body"] = "The method {0} completed unsuccessfully".format(method)

	client.success = client.response["success"]