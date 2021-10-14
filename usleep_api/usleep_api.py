import logging
logger = logging.getLogger("USleepAPI")

import os
import time
import requests
import json
from bs4 import BeautifulSoup


class USleepAPI:
    def __init__(self, api_token, session_name=None, validate_token=True, url="https://sleep.ai.ku.dk:443"):
        self.url = url.rstrip("/")
        self.requests_session = requests.sessions.Session()
        self.session_name = session_name
        self.token = api_token
        self.csrf_token = self.get_csrf_token()
        if validate_token:
            self.validate_token()

    def new_session(self, session_name):
        return USleepAPI(api_token=self.token,
                         url=self.url,
                         session_name=session_name,
                         validate_token=False)

    def validate_token(self):
        logger.info("Validating auth token...")
        response = self.get("/api/v1/token/validate")
        if response.status_code != 200 or not response.content.decode("utf-8").startswith("OK"):
            raise ConnectionRefusedError("Invalid authentication token specified.")

    def get_csrf_token(self):
        response = self.get("/login", as_json=False, log_response=False)
        soup = BeautifulSoup(response.content, "html.parser")
        csrf_token = soup.find('input', attrs={"id": 'csrf_token'}).get('value')
        return csrf_token

    def _add_token_to_headers(self, headers=None):
        headers = headers or {}
        headers['Authorization'] = f"JWT {self.token}"
        return headers

    def _add_csrf_to_headers(self, headers=None):
        headers = headers or {}
        headers['X-CSRFToken'] = self.csrf_token
        return headers

    def _add_session_to_params(self, params=None):
        params = params or {}
        params['session_name'] = f"{self.session_name}"
        return params

    @staticmethod
    def _log_response(response, type_):
        logger_method = logger.info if response.status_code == 200 else logger.error
        try:
            content = "[JSON data] " + str(response.json())[:50] + " ..."
        except json.JSONDecodeError:
            content = response.content.decode('utf-8')
        logger_method(f"Server response to {type_}: {content}")

    def get(self, endpoint, as_json=False, log_response=True):
        uri = f"{self.url}/{endpoint.lstrip('/')}"
        headers, params = {}, {}
        if self.token:
            headers = self._add_token_to_headers(headers)
        if self.session_name:
            params = self._add_session_to_params(params)
        response = self.requests_session.get(uri, headers=headers, params=params)
        if log_response:
            self._log_response(response, type_="GET")
        if as_json and response.status_code == 200:
            return response.json()
        else:
            return response

    def post(self, endpoint, headers=None, data=None, json=None, files=None, params=None):
        uri = f"{self.url}/{endpoint.lstrip('/')}"
        headers = self._add_csrf_to_headers(headers)
        if self.token:
            headers = self._add_token_to_headers(headers)
        if self.session_name:
            params = self._add_session_to_params(params)
        response = self.requests_session.post(uri, data,
                                              files=files,
                                              json=json,
                                              params=params,
                                              headers=headers)
        self._log_response(response, type_="POST")
        return response

    def get_model_names(self):
        return self.get("/api/v1/get/model_names", as_json=True)['models']

    def set_model(self, model_str):
        logger.info(f"Setting model '{model_str}'")
        model_names = self.get_model_names()
        if model_str not in model_names:
            err = "Invalid model, must be in {}".format(model_names)
            logger.error(err)
            raise ValueError(err)
        self.post("/api/v1/sleep_stager/set_model", data={'model': model_str})

    def upload_file(self, file_path):
        logger.info(f"Uploading file at path {file_path}. Please wait.")
        with open(file_path, "rb") as in_f:
            return self.post("/api/v1/file/upload", files={'PSG': in_f})

    def delete_file(self):
        return self.post('/api/v1/file/delete')

    def get_configuration_options(self):
        logger.info("Getting configuration")
        return self.get("/api/v1/get/configuration_options", as_json=True)

    def get_status(self):
        return self.get("/api/v1/get/prediction_status", as_json=True)

    def get_hypnogram(self):
        response = self.get("/api/v1/get/hypnogram")
        if response.status_code == 200:
            response = response.json()
        return response

    def stream_prediction_log(self, verbose=True):
        full_log = []

        def stream(delay_sec=0):
            """ Returns True if 'stream' should be called again, False otherwise """
            time.sleep(delay_sec)
            response = self.get('/api/v1/get/prediction_log', log_response=False)
            if response.status_code != 200:
                raise ValueError(response.content)
            response = response.json()
            lines = response['lines'].replace("<br>", "\n")
            if lines:
                if verbose:
                    print(lines)
                full_log.append(lines)
            return not response['finished']
        continue_stream = stream()
        while continue_stream:
            continue_stream = stream(delay_sec=2)
        return "".join(full_log)

    def wait_for_completion(self):
        logger.info("Waiting for prediction completion...")
        self.stream_prediction_log(verbose=False)
        return self.get_status()['label'].lower() == "completed"

    def get_session_names(self):
        return self.get('/api/v1/sleep_stager/get_session_names', as_json=True)['session_names']

    def delete_session(self):
        return self.post('/api/v1/sleep_stager/delete_session')

    def delete_all_sessions(self):
        for session in self.get_session_names():
            self.new_session(session).delete_session()

    def download_hypnogram(self, out_path, file_type='tsv'):
        file_type = file_type.strip(".")
        assert file_type in ("tsv", "hyp", "npy"), "Invalid file format"
        # Download file
        response = self.get(f'/api/v1/download/hypnogram_{file_type}', log_response=False)
        if response.status_code == 200:
            # Save file to disk
            out_path = os.path.splitext(out_path)[0] + f".{file_type}"
            logger.info(f"Saving file to {out_path}")
            with open(out_path, "wb") as out_f:
                out_f.write(response.content)
        else:
            raise ValueError(response.content)

    def predict(self, channel_groups, data_per_prediction):
        data = {'data_per_prediction': int(data_per_prediction)}
        entry_count = 0
        for group_idx, group in enumerate(channel_groups):
            for channel in group:
                data[f'channels-{entry_count}'] = channel
                data[f'channel_group_idx-{entry_count}'] = group_idx
                entry_count += 1
        return self.post("/api/v1/sleep_stager/predict", data=data)
