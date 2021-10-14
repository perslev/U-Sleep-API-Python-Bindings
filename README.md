# U-Sleep API Python Bindings
Python bindings to the U-Sleep Webserver API


## Purpose
An experimental/minimal implementation of Python bindings to the U-Sleep Webserver ([https://sleep.ai.ku.dk]()) API.

## Authentication
All requests to any API endpoints must include an API authentication token. Obtain your token by:

1. Log in to your account at [https://sleep.ai.ku.dk/login]().
2. Select "Account" and "Generate API Token" from the drop-down menu.
3. Paste the API token into your script.

At the time of writing the obtained token is valid for 12 hours. Once expired, a new token must be generated following the above procedure.

Keep your token(s) private as they represent your identity to the server and allows others to authenticate on yout behalf.

## Example

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