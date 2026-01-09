from flask import Flask , request, jsonify
import statbotics, json
import time

import redis

sb = statbotics.Statbotics()
r = redis.Redis(host='192.168.100.2', port=6379, decode_responses=True)


app = Flask(__name__)
g_webhook_data = {}
predictMan = PredictionManager()

    # Define a route and a view function
@app.route('/tba', methods=["POST", "GET"])
def notifyMatchStart():
    # If the request was not POST
    if request.method != "POST":
        return jsonify({"get": "method"}), 200
        
    g_webhook_data = request.json

    #   upcoming match
    if g_webhook_data["message_type"] == "upcoming_match":
        getUpcomingMatchData(g_webhook_data)
        return {"success": "success"}, 200
    #   match score
    elif g_webhook_data["message_type"] == "match_score":
        #get match prediction for the match that is recieved
        predictMan.Statbotics.updateAccuracy(g_webhook_data["message_data"]["match_key"])
        return {"success": "success"}, 200 
    else:
        return jsonify({"fail": "failed"}), 200

#    Get upcoming match data and send prediction to the statbotics handler
def getUpcomingMatchData(webhook_data):
    try:
        scheduled_time = webhook_data["message_data"]["scheduled_time"]
        print("Scheduled Time: " + time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(scheduled_time)))
    except:
        print("failed to retrieve start time, but there is a match in ~7min")
    predictMan.Statbotics.getMatchPrediction(webhook_data["message_data"]["match_key"])

#TO FIND STATBOTICS ACCURACY, THE KEY IS "statboticsAccuracy"

#NEW CLASS SYSTEM
class Statbotics:
    def __init__(self):
        pass
    def getEPA(self,team):
        try:
            data = sb.get_team(team)
            print(data["norm_epa"]["current"])
        except:
            print('not found')

    def getMatchPrediction(self,matchID):
        redTeamWinningProb = float(sb.get_match(matchID,["pred"])["pred"]["red_win_prob"])
        predictedWinner = ""
        #get winning probability
        if  redTeamWinningProb >= 0.5:
            predictedWinner = "red"
        else:
            predictedWinner = "blue"
        r.hset(matchID, mapping={
            "matchID":matchID,
            'predictedWinner': predictedWinner,
            "redTeamWinningProb": redTeamWinningProb,
        })

    def updateAccuracy(self,matchID):
        #if the acuracy was already checked, return early as accuracy should not be checked again
        if r.hget(matchID,"wasStatboticsCorrect") != None or r.hget(matchID,"matchID") == None:
            return
        #find and update winner
        winner = sb.get_match(matchID,["result"])["result"]["winner"]
        r.hset(matchID, "actualWinner", winner)
        #update the match info to have is_statbotics correct section
        redTeamWinningProb = r.hgetall(matchID)["redTeamWinningProb"]
        if (float(redTeamWinningProb) >= 0.5 and winner == "red") or (float(redTeamWinningProb) <= 0.5 and winner == "blue"):
            wasStatboticsCorrect = "yes"
        else:
            wasStatboticsCorrect = "no"
        r.hset(matchID, "wasStatboticsCorrect", wasStatboticsCorrect)
        #update overall statbotics accuracy
        if r.hgetall("statboticsAccuracy") == {}:
            r.hset("statboticsAccuracy", mapping={
                "numCorrectPredictions":0,
                'numIncorrectPredictions': 0,
                "statboticsTotalAccuracy": 0.0,
            })
        databaseCorrectPredictions = int(r.hget("statboticsAccuracy","numCorrectPredictions"))
        databaseIncorrectPredictions = int(r.hget("statboticsAccuracy","numIncorrectPredictions"))
        if wasStatboticsCorrect == "yes":
            databaseCorrectPredictions += 1
            r.hset("statboticsAccuracy", "numCorrectPredictions", databaseCorrectPredictions)
        else:
            databaseIncorrectPredictions += 1
            r.hset("statboticsAccuracy", "numIncorrectPredictions", databaseIncorrectPredictions)
        newStatboticsTotalAccuracy = databaseCorrectPredictions/(databaseIncorrectPredictions + databaseCorrectPredictions)
        r.hset("statboticsAccuracy", "statboticsTotalAccuracy", newStatboticsTotalAccuracy)

class tba:
    def __init__(self):
        pass

class PredictionManager:
    def __init__(self):
        self.Statbotics = Statbotics()
        self.tba = tba()
