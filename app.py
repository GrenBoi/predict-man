from flask import Flask , request, jsonify
import statbotics, json
import time, requests

import redis

sb = statbotics.Statbotics()
r = redis.Redis(host='192.168.100.2', port=6379, decode_responses=True)
predictionAPIurl = "https://match.api.apisb.me/prediction"


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
            'statboticsPredictedWinner': predictedWinner,
            "statboticsRedTeamWinningProb": redTeamWinningProb,
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

class Tba:
    def __init__(self):
        pass

class PredictionAPI:
    def __init__(self):
        pass
    def getMatchPrediction(self, match_data):
        teams = match_data["team_keys"]
        matchID = match_data["match_key"]
        payload = {
           "team-red-1" : teams[0],
           "team-red-2" : teams[1],
           "team-red-3" : teams[2],
            "team-blue-1" : teams[3],
            "team-blue-2" : teams[4],
            "team-blue-3" : teams[5]
        }
        response = requests.post(predictionAPIurl, payload)
        inputMatchPrediction(response.json(), matchID)
        
    def inputMatchPrediction(self, returnJson, matchID):
        predictionJsonData = getPredictionFromJson(returnJson)#api code to get prediction
        r.hset(matchID, "predictionAPIPredictedWinner", predictionJsonData[0])
        r.hset(matchID, "predictionAPIPredictedWinnerProbability", predictionJsonData[1])
    
    def updateAccuracy(self,matchID):
        if r.hget(matchID,"waspredictionAPICorrect") != None or r.hget(matchID,"matchID") == None:
            return
        winner = sb.get_match(matchID,["result"])["result"]["winner"]
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

    def getPredictionFromJson(self,input_predictionJsonData):
        if input_predictionJsonData["red_alliance_win_confidence"] > input_predictionJsonData["blue_alliance_win_confidence"]:
            if input_predictionJsonData["draw_confidence"] > input_predictionJsonData["red_alliance_win_confidence"]:
                return ("draw",input_predictionJsonData["draw_confidence"])
            else:
                return("red",red_alliance_win_confidence)
        else:#blue is more than red
            if input_predictionJsonData["draw_confidence"] > input_predictionJsonData["blue_alliance_win_confidence"]:
                return ("draw",input_predictionJsonData["draw_confidence"])
            else:
                return ("blue",input_predictionJsonData["blue_alliance_win_confidence"])


class PredictionManager:
    def __init__(self):
        self.Statbotics = Statbotics()
        self.Tba = Tba()
        self.PredictionAPI = PredictionAPI()



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
    predictMan.PredictionAPI.getMatchPrediction(webhook_data["message_data"])
#TO FIND STATBOTICS ACCURACY, THE KEY IS "statboticsAccuracy"



