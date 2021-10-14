# U-Sleep API Python Bindings
Python bindings to the U-Sleep Webserver API


## Purpose
An experimental/minimal implementation of Python bindings to the U-Sleep Webserver ([https://sleep.ai.ku.dk](https://sleep.ai.ku.dk)) API.

**Under development: The Web API and Python bindings are subject to rapid changes.**

## API Overview

### Sessions

All endpoints accept the query parameter `?session_name=[SESSION_NAME]`. Each stores information on which model to use, what file to predict on and handles to output log- and hypnogram files.
Each user may have (at the time of writing) 5 active sessions.

If no session is specified, the `'default'` session name is used. Note that the `'default'` session is also used by the browser when accessing U-Sleep at [https://sleep.ai.ku.dk](https://sleep.ai.ku.dk).

### Endpoints

- `GET` - `/api/v1/get/model_names` - Get a list of available models.
- `GET` - `/api/v1/get/configuration_options` - Get configuration options for model & file.
- `GET` - `/api/v1/get/prediction_status` - Get prediction process status.
- `GET` - `/api/v1/get/hypnogram` - Get hypnogram after prediction completion.
- `GET` - `/api/v1/get/prediction_log` - Get the prediction log.
- `GET` - `/api/v1/token/validate` - To test if a token is valid.
- `GET` - `/api/v1/sleep_stager/get_session_names` - Get a list of active sessions.
- `POST` - `/api/v1/file/upload` - Upload a file to predict on in a session.
- `POST` - `/api/v1/file/delete` - Delete an uploaded file in a session.
- `POST` - `/api/v1/sleep_stager/set_model` - Specify which model to use in a session.
- `POST` - `/api/v1/sleep_stager/delete_session` - Delete a session and its data.
- `POST` - `/api/v1/sleep_stager/predict` - Start prediction process on session.

Download:

- `GET` - `/api/v1/download/<resource>` - Download `resource` in a session.

Account:

- `POST` - `/api/v1/account/delete` - Permanently delete your account and its data. 

### Example

```bash
curl -s -X GET -H "Authorization: jwt [API TOKEN]" https://sleep.ai.ku.dk/api/v1/get/model_names
>> {"models":["U-Sleep v1.0"]}
```


## Authentication
Requests to any API endpoint must include an API authentication token. Obtain your token by:

1. Log in to your account at [https://sleep.ai.ku.dk/login](https://sleep.ai.ku.dk/login).
2. Select "Account" and "Generate API Token" from the drop-down menu.
3. Paste the API token into your script.

At the time of writing the obtained token is valid for 12 hours. Once expired, a new token must be generated following the above procedure.

Keep your token(s) private as they represent your identity to the server and allows others to authenticate on yout behalf.

## Python Bindings Example

The `USleepAPI` class provides bindings for most of the API endpoints and may be used, e.g., as follows:

```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_example")

from usleep_api import USleepAPI


if __name__ == "__main__":
    file_path = "./my_psg.edf"        # Insert here
    api_token = "eyJ0eXAiOiJKV1Q..."  # Insert here

    # Create a sleep stager object and a new session
    sleep_stager = USleepAPI(personal_access_token=api_token,
                             session_name="my_session")

    # See a list of valid models and set which model to use
    logger.info("Available models: {}".format(sleep_stager.get_model_names())
    sleep_stager.set_model('U-Sleep v1.0')

    # Upload a local file (usually .edf format)
    sleep_stager.upload_file(file_path)

    # Start the prediction on two channel groups:
    #   1: EEG Fpz-Cz + EOG horizontal
    #   2: EEG Pz-Oz + EOG horizontal
    # Using 30 second windows (note: U-Slep v1.0 uses 128 Hz re-sampled signals)
    sleep_stager.predict(channel_groups=[['EEG Fpz-Cz', 'EOG horizontal'],
                                         ['EEG Pz-Oz', 'EOG horizontal']],
                         data_per_prediction=128*30)

    # Wait for the job to finish or stream to the log output
    # sleep_stager.stream_prediction_log()
    success = sleep_stager.wait_for_completion()

    if success:
        # Fetch hypnogram
        hyp = sleep_stager.get_hypnogram()
        logger.info(hyp['hypnogram'])

        # Download hypnogram file
        sleep_stager.download_hypnogram(out_path='./hypnogram', file_type='tsv')
    else:
        logger.error("Prediction failed.")

    # Delete session (i.e., uploaded file, prediction and logs)
    sleep_stager.delete_session()
```