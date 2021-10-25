import logging
logger = logging.getLogger("USleepAPI")

import os
import time
import requests
import json
from json import JSONDecodeError
from bs4 import BeautifulSoup


class USleepAPI:
    def __init__(self, api_token, session_name="default", validate_token=True, url="https://sleep.ai.ku.dk:443"):
        self.url = url.rstrip("/")
        self.requests_session = requests.sessions.Session()
        self.session_name = session_name
        self.api_token = api_token
        if validate_token:
            self.validate_token()

    def new_session(self, session_name):
        return USleepAPI(api_token=self.api_token,
                         url=self.url,
                         session_name=session_name,
                         validate_token=False)

    def validate_token(self):
        logger.info("Validating auth token...")
        response = self.get("/api/v1/info/ping")
        if response.status_code != 200:
            raise ConnectionRefusedError("Invalid authentication token specified.")

    def _add_token_to_headers(self, headers=None):
        headers = headers or {}
        headers['Authorization'] = f"Bearer {self.api_token}"
        return headers

    @staticmethod
    def _log_response(response, type_):
        logger_method = logger.info if response.status_code in (200, 201) else logger.error
        try:
            content = "[JSON data] " + str(response.json())[:50] + " ..."
        except json.JSONDecodeError:
            content = response.content.decode('utf-8')
        logger_method(f"Server response to {type_}: {content}")

    def _request(self, endpoint, method, as_json=False, log_response=True, headers=None, **kwargs):
        uri = f"{self.url}/{endpoint.lstrip('/')}"
        method = method.upper()
        if method == "GET":
            request_method = self.requests_session.get
        elif method == "POST":
            request_method = self.requests_session.post
        elif method == "DELETE":
            request_method = self.requests_session.delete
        else:
            raise ValueError(f"Method {method} is not supported.")
        if self.api_token:
            headers = self._add_token_to_headers(headers)
        response = request_method(uri, headers=headers, **kwargs)
        if log_response:
            self._log_response(response, type_=method)
        if as_json:
            try:
                return response.json()
            except JSONDecodeError as e:
                raise ValueError("Could not convert response to JSON. "
                                 "The requested resource most likely does not exist. "
                                 "Response code: {}. Response content: '{}'".format(response.status_code,
                                                                                   response.content.decode())) from e
        else:
            return response

    def get(self, endpoint, as_json=False, log_response=True, **kwargs):
        """ Make GET request """
        return self._request(endpoint, method="GET", as_json=as_json, log_response=log_response, **kwargs)

    def post(self, endpoint, as_json=False, log_response=True, **kwargs):
        """ Make POSt request """
        return self._request(endpoint, method="POST", as_json=as_json, log_response=log_response, **kwargs)

    def delete(self, endpoint, as_json=False, log_response=True, **kwargs):
        """ Make DELETE request """
        return self._request(endpoint, method="DELETE", as_json=as_json, log_response=log_response, **kwargs)

    def get_model_names(self):
        return self.get("/api/v1/info/model_names", as_json=True)['models']

    def set_model(self, model_str):
        logger.info(f"Setting model '{model_str}'")
        model_names = self.get_model_names()
        if model_str not in model_names:
            err = "Invalid model, must be in {}".format(model_names)
            logger.error(err)
            raise ValueError(err)
        self.post(f"/api/v1/sleep_stager/{self.session_name}/set_model", data={'model': model_str})

    def upload_file(self, file_path):
        logger.info(f"Uploading file at path {file_path}. Please wait.")
        with open(file_path, "rb") as in_f:
            return self.post(f"/api/v1/sleep_stager/{self.session_name}/file", files={'PSG': in_f})

    def delete_file(self):
        return self.delete(f"/api/v1/sleep_stager/{self.session_name}/file")

    def get_configuration_options(self):
        logger.info("Getting configuration")
        return self.get(f"/api/v1/sleep_stager/{self.session_name}/configuration_options", as_json=True)

    def get_status(self):
        return self.get(f"/api/v1/sleep_stager/{self.session_name}/prediction_status", as_json=True)

    def get_hypnogram(self):
        response = self.get(f"/api/v1/sleep_stager/{self.session_name}/hypnogram")
        if response.status_code == 200:
            response = response.json()
        return response

    def get_prediction_log(self):
        return self.get(f'/api/v1/sleep_stager/{self.session_name}/prediction_log', as_json=True)['log']

    def stream_prediction_log(self, verbose=True):
        full_log = []

        def stream(delay_sec=0):
            """ Returns True if 'stream' should be called again, False otherwise """
            time.sleep(delay_sec)
            response = self.get(f"/api/v1/sleep_stager/{self.session_name}/prediction_log_stream", log_response=False)
            if response.status_code != 200:
                raise ValueError(response.content)
            response = response.json()
            log = response['log']
            if log:
                if verbose:
                    print(log)
                full_log.append(log)
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
        return self.get(f"/api/v1/sleep_stager/session_names", as_json=True)['session_names']

    def get_session_details(self):
        return self.get(f"/api/v1/sleep_stager/{self.session_name}", as_json=True)

    def delete_session(self):
        return self.delete(f"/api/v1/sleep_stager/{self.session_name}")

    def delete_all_sessions(self):
        for session in self.get_session_names():
            self.new_session(session).delete_session()

    def download_hypnogram(self, out_path, file_type='tsv'):
        file_type = file_type.strip(".")
        assert file_type in ("tsv", "hyp", "npy"), "Invalid file format"
        # Download file
        response = self.get(endpoint=f"/api/v1/sleep_stager/{self.session_name}/download/hypnogram_{file_type}",
                            log_response=False)
        if response.status_code == 200:
            # Save file to disk
            out_path = os.path.splitext(out_path)[0] + f".{file_type}"
            logger.info(f"Saving file to {out_path}")
            with open(out_path, "wb") as out_f:
                out_f.write(response.content)
        else:
            raise ValueError(response.content.decode())

    def predict(self, channel_groups, data_per_prediction):
        data = {'data_per_prediction': int(data_per_prediction)}
        entry_count = 0
        for group_idx, group in enumerate(channel_groups):
            for channel in group:
                data[f'channels-{entry_count}'] = channel
                data[f'channel_group_idx-{entry_count}'] = group_idx
                entry_count += 1
        return self.post(f"/api/v1/sleep_stager/{self.session_name}/predict", data=data)
