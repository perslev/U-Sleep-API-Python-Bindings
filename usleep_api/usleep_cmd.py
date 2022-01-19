import logging
logger = logging.getLogger(__name__)

import sys
import os
from pathlib import Path
from argparse import ArgumentParser
from usleep_api import USleepAPI


def get_argparser():
    parser = ArgumentParser(
        usage="U-Sleep command line interface to the U-Sleep Web API. May be used to perform sleep stage scoring of "
              "EDF(+) files using the U-Sleep webserver at https://sleep.ai.ku.dk.\n\n"
              "Authentication: An API access token must be created at https://sleep.ai.ku.dk. Store the token in an "
              "environment variable of name specified by the '--api-token-env-name' flag (default 'USLEEP_API_TOKEN') "
              "or pass the token to the --token flag (not recommended).\n\n"
              "Basic usage:\n"
              ">> usleep-api [input file path] [output file path]\n\n"
              "Examples:\n"
              ">> usleep-api ./my_psg.edf ./hypnogram.tsv\n"
              ">> usleep-api ./my_psg.edf ./hypnogram.tsv\n"
              ">> usleep-api ./my_psg.edf ./hypnogram.tsv -l prediction_log.txt\n"
              ">> usleep-api ./my_psg.edf ./hypnogram.tsv --print-hypnogram\n"
              ">> usleep-api ./my_psg.edf ./hypnogram.tsv --log-level=ERROR\n"
              ">> usleep-api ./my_psg.edf ./hypnogram.tsv --anonymize-before-upload\n"
              ">> usleep-api ./my_psg.edf ./hypnogram.tsv --channel-groups C3-A2++EOG C4-A1++EOG F3-A2++EOG\n"
              ">> usleep-api ./my_psg.edf ./hypnogram.txt --data-per-prediction 128"
    )
    parser.add_argument("input file path", type=str, help="Path to input EDF(+) (.edf) file to score.")
    parser.add_argument("output file path", type=str, help="Path to output file, e.g., 'hypnogram.tsv'. "
                                                           "Extension must be one of [.tsv, .txt, .npy].")
    parser.add_argument("-l", '--log-file-path', type=str, help="Optional path to save prediction process log to.")
    parser.add_argument("--print-hypnogram", action="store_true", help="Print the scored hypnogram to stdout.")
    parser.add_argument("--overwrite-file", action="store_true", help="Overwrite any existing output prediction "
                                                                      "and/or log files. Otherwise, raises an error"
                                                                      " if a file already exists.")
    parser.add_argument("--model", type=str, default='U-Sleep v1.0', help="Model to use for scoring. Default is 'U-Sleep v1.0'.")
    parser.add_argument("--data-per-prediction", type=int, default=128*30,
                        help="Number of data points (in re-sampled signal, 128 Hz for U-Sleep v1.0) to use for each "
                             "prediction. Default is 128*30 = 3840, i.e., 1 prediction/sleep stage pr. 30 seconds.")
    parser.add_argument("--anonymize-before-upload", action="store_true",
                        help="Anonymize the input file before uploading to the server. "
                             "This creates a temporary file and does not modify the original file. "
                             "Note: The EDF file will be anonymized with respect to: Patient ID, sex, name and DOB "
                             "as well as equipment, admin, and technician codes, recording date and time. Events and "
                             "channel names are NOT anonymized. Default is False (upload file as-is).")
    parser.add_argument("--channel-groups", type=str, nargs="*", default=None,
                        help="An optional space-separated list of channel groups. Each group is a string of format: "
                             "{channel1}++{channel2} in the case of a 2-channel group. Each group of channels are "
                             "individually passed to the model for scoring and a majority vote over all predictions "
                             "are output. Example: '--channel-groups C3-M2++EOG C4-M1++EOG' will run the scoring on 2 "
                             "sets of 2 channels. "
                             "Usually, more groups lead to better scoring accuracy. Default is None, in "
                             "which case all suitable combinations of channels are automatically inferred if possible"
                             " (this may fail if the channel type is not easily inferred from its channel name).")
    parser.add_argument("--api-token-env-name", type=str, default="USLEEP_API_TOKEN",
                        help="Name of environment variable that stores the U-Sleep API token. Token may also be "
                             "explicitly passed using the --token flag (not recommended). "
                             "Default is 'USLEEP_API_TOKEN'.")
    parser.add_argument("--token", type=str, default=None,
                        help="Explicitly pass the U-Sleep API token. Not recommended as the token will be visible in "
                             "the terminal history.")
    parser.add_argument("--stream-log", action="store_true",
                        help="Stream the prediction log from the server during prediction.")
    parser.add_argument("--log-level", type=str,
                        default="INFO", choices=['CRITICAL', 'ERROR', 'WARN', 'WARNING', 'INFO', 'DEBUG'],
                        help="Specify the logging level. Default='INFO'.")
    return parser


def init_logging(level):
    # Set logging (done here to set level base don cmd input)
    logging.basicConfig(format="%(levelname)s | %(asctime)s | %(message)s",
                        datefmt="%Y/%m/%d %H:%M:%S",
                        level=level)
    logger = logging.getLogger(__name__)
    return logger


def entry_func():
    args = vars(get_argparser().parse_args(sys.argv[1:]))
    logger = init_logging(args['log_level'])
    logger.info(f"Running with args: {args}")
    in_path = Path(args['input file path']).absolute()
    if not in_path.exists() or in_path.suffix != ".edf":
        raise OSError(f"Input file at '{args['input file path']}' does not exist or is not a '.edf' file "
                      f"(currently only supported file type).")
    out_path = Path(args['output file path']).absolute()
    if out_path.suffix not in (".tsv", ".txt", ".npy"):
        raise ValueError(f"Out file path must have extension in ('.tsv', '.txt', '.npy'), got '{out_path.suffix}'")
    overwrite = args['overwrite_file']
    if out_path.exists() and not overwrite:
        raise OSError(f"Output hypnogram file at '{out_path}' already exists and the --overwrite-file flag was not set.")
    if args['log_file_path']:
        log_file_path = Path(args['log_file_path']).absolute()
        if log_file_path.exists() and not overwrite:
            raise OSError(f"Output log file at '{out_path}' already exists and the --overwrite-file flag was not set.")
    else:
        log_file_path = None
    logger.info(f"Input file:          {in_path}")
    logger.info(f"Output file:         {out_path}")
    logger.info(f"Prediction log file: {log_file_path}")

    api = USleepAPI(api_token=args['token'] or os.environ[args['api_token_env_name']])
    hypnogram, log = api.quick_predict(
        input_file_path=in_path,
        output_file_path=out_path,
        model=args['model'],
        anonymize_before_upload=args['anonymize_before_upload'],
        data_per_prediction=args['data_per_prediction'],
        channel_groups=[c.split("++") for c in args['channel_groups']] if args['channel_groups'] else None,
        stream_log=args['stream_log'],
        log_file_path=log_file_path
    )
    if args['print_hypnogram']:
        print(hypnogram)


if __name__ == "__main__":
    entry_func()
