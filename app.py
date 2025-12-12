from flask import Flask , request, jsonify, render_template
import statbotics, json
import time

import redis

sb = statbotics.Statbotics()
r = redis.Redis(host='192.168.100.2', port=6379, decode_responses=True)

# True
#r.get('foo')
# bar
#print(r.get('foo'))
#for team in range(350,400):
#    print(str(team) + ": " + r.get(team))
#    try:
#        data = sb.get_team(team)
#        r.set(team, data["norm_epa"]["current"])
#    except:
#        r.set(team, 'not found')
#print(r.get("364"))
#r.hset('user-session:123', mapping={
#    'name': 'John',
#    "surname": 'Smith',
#    "company": 'Redis',
#    "age": 29
#})

#r.hgetall('user-session:123')
# {'surname': 'Smith', 'name': 'John', 'company': 'Redis', 'age': '29'}

r.close()
app = Flask(__name__)
g_webhook_data = {}


    # Define a route and a view function
@app.route('/tba', methods=["POST", "GET"])
def notifyMatchStart():
    predictMan = PredictionManager()
    # Webhook data is typically sent in the request body as JSON
    if request.method == "POST":
        g_webhook_data = request.json
        if g_webhook_data["message_type"] == "upcoming_match":
            #print("Received webhook data:", g_webhook_data)
            try:
                scheduled_time = g_webhook_data["message_data"]["scheduled_time"]
                print("Scheduled Time: " + time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(scheduled_time)))
            except:
                print("failed to retrieve start time, but there is a match in ~7min")
            predictMan.statbotics.getMatchPrediction(g_webhook_data["message_data"]["match_key"])
            return {"success": "success"}, 200
        elif g_webhook_data["message_type"] == "match_score":
            #print("Received webhook data:", g_webhook_data)
            predictMan.statbotics.updateAccuracy(g_webhook_data["message_data"]["match_key"])#get match prediction for the match that is recieved
            return {"success": "success"}, 200
        else:
            return jsonify({"fail": "failed"}), 200
    else:
        return jsonify({"get": "method"}), 200

def getAllPredictions(webhook_data):
    return ["Match " + webhook_data["message_data"]["match_key"],sb.get_match(webhook_data["message_data"]["match_key"],["pred"])]


#STATBOTICS ACCURACY KEY IS "statboticsAccuracy"

#NEW CLASS SYSTEM
class statbotics:
    def __init__(self):
        pass

    def getEPA(self,team):
        #r.set(team, data["norm_epa"]["current"])
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
        self.statbotics = statbotics()
        self.tba = tba()

keys_list = ['2024necmp_f1m1', '2024necmp_f1m2', '2024necmp_f1m3',"2024necmp_f1m4","2023necmp_f1m1"
,"2023necmp_f1m2","2023necmp_f1m3","2024casj_qm1","2024casj_qm2","2024casj_qm3","2024casj_qm4"]
#r.delete(*keys_list)

predict364 = PredictionManager()
print(r.hgetall("2024necmp_f1m1"))
print(r.hgetall("2024necmp_f1m2"))
#r.delete("2024necmp_f1m3")
print(r.hgetall("2024necmp_f1m3"))
print(r.hgetall("2024casj_qm1"))
print(r.hgetall("2024casj_qm2"))
print(r.hgetall("2024casj_qm3"))
print(r.hgetall("2024casj_qm4"))
print(r.hgetall("statboticsAccuracy"))
#print(sb.get_match("2024casj_qm4"))
