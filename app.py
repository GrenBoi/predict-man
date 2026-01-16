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
def recieveNotificationTBA():
    # If the request was not POST
    if request.method != "POST":
        return jsonify({"get": "method"}), 200

    g_webhook_data = request.json
    if g_webhook_data["message_type"] == "verification":
        print(g_webhook_data)
        return {"success": "success"}, 200
    #   upcoming match
    if g_webhook_data["message_type"] == "upcoming_match":
        getUpcomingMatchData(g_webhook_data)
        return {"success": "success"}, 200
    #   match score
    elif g_webhook_data["message_type"] == "match_score":
        # get match prediction for the match that is recieved
        predictMan.Statbotics.update_accuracy(
            g_webhook_data["message_data"]["match_key"]
        )
        predictMan.PredictionAPI.update_accuracy(
            g_webhook_data["message_data"]["match_key"]
        )
        return {"success": "success"}, 200
    else:
        return jsonify({"fail": "failed"}), 400


# add payload with {match_key: "(match key/match id)"}
@app.route("/average_match_prediction", methods=["POST", "GET"])
def sendMatchPrediction():
    inputtedInfo = request.json
    if "match_key" in inputtedInfo:
        averageMatchPrediction = predictMan.average_prediction(inputtedInfo["match_key"])
        if averageMatchPrediction is None:
            return jsonify(
                {"Server failed to compute averages, Internal Server Error": 404}
            )
        return jsonify(
            {
                "Average Match Prediction for: "
                + inputtedInfo["match_key"]: averageMatchPrediction
            }
        )
    else:
        return jsonify({"match_key could not be found in incoming json": 400})


#    Get upcoming match data and send prediction to the statbotics handler
def getUpcomingMatchData(webhook_data):
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
    predictMan.Statbotics.calculateMatchPrediction(
        webhook_data["message_data"]
    )
    predictMan.PredictionAPI.calculateMatchPrediction(webhook_data["message_data"])


# TO FIND STATBOTICS ACCURACY, THE KEY IS "statboticsAccuracy"
# TO FIND PREDICTION API ACCURACY, THE KEY IS "predictionApiAccuracy"
keys_list = ['2024necmp_f1m1', '2024necmp_f1m2', '2024necmp_f1m3',"2024necmp_f1m4","2023necmp_f1m1"
,"2023necmp_f1m2","2023necmp_f1m3","2024casj_qm1","2024casj_qm2","2024casj_qm3","2024casj_qm4", "statboticsAccuracy","predictionApiAccuracy","2025wila_f1m1","2025wila_f1m2"]
#r.delete(*keys_list)
all_keys = r.keys('*')
print(f"Found {len(all_keys)} keys.")
#print(f"Found {all_keys} keys.")
for key in all_keys:

    #print(r.hgetall(key))
    #print()

    pass
#print(predictMan.average_prediction("2023necmp_f1m1"))
#print(r.hgetall("2024necmp_f1m2"))
