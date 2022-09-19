import os
import time
import pytz
import requests
import warnings

from auto_stop_workers import start_worker, stop_worker
from prometheus_api_client import PrometheusConnect

warnings.filterwarnings("ignore")

utc = pytz.UTC
NUM_PROCESSED_SUBMISSIONS = "num_processed_submissions"
NUM_SUBMISSIONS_IN_QUEUE = "num_submissions_in_queue"
PROMETHEUS_URL = os.environ.get(
    "MONITORING_API_URL", "https://monitoring-staging.eval.ai/prometheus/"
)

ENV = os.environ.get("ENV", "dev")

evalai_endpoint = os.environ.get("API_HOST_URL")
authorization_header = {
    "Authorization": "Bearer {}".format(os.environ.get("AUTH_TOKEN"))
}

prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)


def execute_get_request(url):
    response = requests.get(url, headers=authorization_header)
    return response.json()


def get_challenges():
    all_challenge_endpoint = (
        "{}/api/challenges/challenge/present/approved/all".format(
            evalai_endpoint
        )
    )
    response = execute_get_request(all_challenge_endpoint)

    return response


def get_queue_length(queue_name):
    try:
        num_processed_submissions = int(
            prom.custom_query(
                f"num_processed_submissions{{queue_name='{queue_name}'}}"
            )[0]["value"][1]
        )
    except Exception:  # noqa: F841
        num_processed_submissions = 0

    try:
        num_submissions_in_queue = int(
            prom.custom_query(
                f"num_submissions_in_queue{{queue_name='{queue_name}'}}"
            )[0]["value"][1]
        )
    except Exception:  # noqa: F841
        num_submissions_in_queue = 0

    return num_submissions_in_queue - num_processed_submissions


def get_queue_length_by_challenge(challenge):
    queue_name = challenge["queue"]
    return get_queue_length(queue_name)


def increase_or_decrease_workers(challenge):
    try:
        queue_length = get_queue_length_by_challenge(challenge)
    except Exception:  # noqa: F841
        print(
            "Unable to get the queue length for challenge ID: {}, Title: {}. Skipping.".format(
                challenge["id"], challenge["title"]
            )
        )
        return

    num_workers = (
        0 if challenge["workers"] is None else int(challenge["workers"])
    )

    print(
        "Num Workers: {}, Queue Length: {}".format(num_workers, queue_length)
    )
    if queue_length == 0:
        if num_workers > 0:
            response = stop_worker(challenge["id"])
            print("AWS API Response: {}".format(response))
            print(
                "Stopped worker for Challenge ID: {}, Title: {}".format(
                    challenge["id"], challenge["title"]
                )
            )
        else:
            print(
                "No workers and queue messages found for Challenge ID: {}, Title: {}. Skipping.".format(
                    challenge["id"], challenge["title"]
                )
            )

    else:
        if num_workers == 0:
            response = start_worker(challenge["id"])
            print("AWS API Response: {}".format(response))
            print(
                "Started worker for Challenge ID: {}, Title: {}.".format(
                    challenge["id"], challenge["title"]
                )
            )
        else:
            print(
                "Existing workers and pending queue messages found for Challenge ID: {}, Title: {}. Skipping.".format(
                    challenge["id"], challenge["title"]
                )
            )


# TODO: Factor in limits for the APIs
def increase_or_decrease_workers_for_challenges(response):
    for challenge in response["results"]:
        if (
            not challenge["is_docker_based"]
            and not challenge["remote_evaluation"]
        ):
            increase_or_decrease_workers(challenge)
            time.sleep(1)

        else:
            print(
                "Challenge ID: {}, Title: {} is either docker-based or remote-evaluation. Skipping.".format(
                    challenge["id"], challenge["title"]
                )
            )


# Cron Job
def start_job():
    response = get_challenges()
    increase_or_decrease_workers_for_challenges(response)
    next_page = response["next"]
    while next_page is not None:
        response = execute_get_request(next_page)
        increase_or_decrease_workers_for_challenges(response)
        next_page = response["next"]


if __name__ == "__main__":
    print("Starting worker auto scaling script")
    start_job()
    print("Quitting worker auto scaling script!")
