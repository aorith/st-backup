import sys
import logging
import requests
import json


class Stapi:
    def __init__(self, apikey, host, port, https):
        self.apikey = apikey
        self.host = host
        self.port = port
        self.https = https

        self.headers = {
            'X-API-Key': self.apikey
        }
        self.url = '{proto}://{host}:{port}'.format(
            proto='https' if https else 'http',
            host=self.host,
            port=self.port
        )

        if  not self.initial_check():
            logging.error("Could not communicate with syncthing rest api, check config")
            sys.exit(1)


    def get(self, endpoint, data=None, headers=None, params=None,
            return_response=False, raw_exceptions=False):
        return self._request('GET', endpoint, data, headers, params,
                            return_response, raw_exceptions)

    def post(self, endpoint, data=None, headers=None, params=None,
            return_response=False, raw_exceptions=False):
        return self._request('POST', endpoint, data, headers, params,
                            return_response, raw_exceptions)

    def _request(self, method, endpoint, data=None, headers=None, params=None,
                    return_response=False, raw_exceptions=False):

        endpoint = self.url + endpoint

        if data is None:
            data = {}

        if headers is None:
            headers = {}

        headers.update(self.headers)

        try:
            resp = requests.request(
                method,
                endpoint,
                data=json.dumps(data),
                params=params,
                headers=headers,
                timeout=10.0
            )

            if not return_response:
                resp.raise_for_status()

        except requests.RequestException as e:
            if raw_exceptions:
                raise e
            logging.error("Error communicating with ST Rest API\n{}".format(e))
            sys.exit(1)
        else:
            if return_response:
                return resp

            if resp.status_code != requests.codes.ok:
                logging.error('%d %s (%s): %s', resp.status_code, resp.reason,
                                resp.url, resp.text)
                return resp

            if 'json' in resp.headers.get('Content-Type', 'text/plain').lower():
                json_data = resp.json()

            else:
                content = resp.content.decode('utf-8')
                if content and content[0] == '{' and content[-1] == '}':
                    json_data = json.loads(content)

                else:
                    return content

            if isinstance(json_data, dict) and json_data.get('error'):
                api_err = json_data.get('error')
                logging.error("Api error: {}".format(api_err))
            return json_data

    def initial_check(self):
        content = self.get('/rest/system/ping', return_response=False)
        return 'pong' in content['ping']
