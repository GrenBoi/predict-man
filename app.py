from flask import Flask, request, jsonify

import time
import requests

import redis

from prediction_manager import PredictionManager
r = redis.Redis(host="192.168.100.2", port=6379, decode_responses=True)

app = Flask(__name__)
g_webhook_data = {}
predictMan = PredictionManager()

# Define a route and a view function
@app.route("/tba", methods=["POST", "GET"])
def recieve_notification_TBA():
    # If the request was not POST
    if request.method != "POST":
        return jsonify({"get": "method"}), 200

    g_webhook_data = request.json
    if g_webhook_data["message_type"] == "verification":
        print(g_webhook_data)
        return {"success": "success"}, 200
    #   upcoming match
    if g_webhook_data["message_type"] == "upcoming_match":
        get_upcoming_match_data(g_webhook_data)
        return {"success": "success"}, 200
    #   match score
    elif g_webhook_data["message_type"] == "match_score":
        # get match prediction for the match that is recieved
        predictMan.Statbotics_Manager.update_accuracy(
            g_webhook_data["message_data"]["match_key"]
        )
        predictMan.PredictionAPI_Manager.update_accuracy(
            g_webhook_data["message_data"]["match_key"]
        )
        return {"success": "success"}, 200
    else:
        return jsonify({"fail": "failed"}), 400


# add payload with {match_key: "(match key/match id)"}
@app.route("/average_match_prediction", methods=["POST", "GET"])
def send_match_prediction():
    inputted_info = request.json
    if "match_key" in inputted_info:
        average_match_prediction = predictMan.average_prediction(inputted_info["match_key"])
        if average_match_prediction is None:
            return jsonify(
                {"Server failed to compute averages, Internal Server Error": 404}
            )
        return jsonify(
            {
                "Average Match Prediction for: "
                + inputted_info["match_key"]: average_match_prediction
            }
        )
    else:
        return jsonify({"match_key could not be found in incoming json": 400})


#    Get upcoming match data and send prediction to the statbotics handler
def get_upcoming_match_data(webhook_data):
    """Takes in TBA data and prints out the scheduled time of competition as well as passing data to the PredictionManager"""
    try:
        scheduled_time = webhook_data["message_data"]["scheduled_time"]
        print(
            "Scheduled Time: "
            + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(scheduled_time))
            + "\n"
        )
    except KeyError:
        print("failed to retrieve start time, but there is a match in ~7min")
    predictMan.Statbotics_Manager.calculate_match_prediction(
        webhook_data["message_data"]
    )
    predictMan.PredictionAPI_Manager.calculate_match_prediction(webhook_data["message_data"])


# TO FIND STATBOTICS ACCURACY, THE KEY IS "statbotics_accuracy"
# TO FIND PREDICTION API ACCURACY, THE KEY IS "prediction_api_accuracy"