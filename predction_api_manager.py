import redis
import statbotics

predictionAPIurl = "https://match.api.apisb.me/prediction"
r = redis.Redis(host="192.168.100.2", port=6379, decode_responses=True)
sb = statbotics.Statbotics()

class PredictionAPI_Manager:
    def __init__(self):
        pass

    def fetch_prediction(self, matchID):  
        """

        Takes in match_key from TBA
        fetch_prediction Function is used for average predictions. Gets probability of red winning for a match and returns it in a tuple
        Tuple Format: (winnerPredict, red is winner probability, totalAccuracy), if match does not exist, return None

        """

        if r.hexists(matchID, "predictionAPIPredictedWinner"):
            winProbability = r.hget(matchID, "predictionAPIPredictedWinnerProbability")
            if r.hget(matchID, "predictionAPIPredictedWinner") == "blue":
                # changes red probability of win to blue for format
                winProbability = 1 - r.hget(
                    matchID, "predictionAPIPredictedWinnerProbability"
                )
            return (
                r.hget(matchID, "predictionAPIPredictedWinner"),
                winProbability,
                r.hget("predictionApiAccuracy", "predictionApiTotalAccuracy"),
            )
        else:
            return None

    def calculateMatchPrediction(self, match_data):
        """
        
        Takes in Match Data from TBA
        calculate_match_prediction Function is used to put initial match prediction data into Redis. 
        Is called from TBA by upcoming_match notification
        Calls predictionAPI to get a json file in this format:
        {
            blue_alliance_win_confidence : 
            draw_confidence : 
            red_alliance_win_confidence : 
        }
        
        """
        teams = match_data["team_keys"]
        matchID = match_data["match_key"]
        payload = {
            "team-red-1": teams[0],
            "team-red-2": teams[1],
            "team-red-3": teams[2],
            "team-blue-1": teams[3],
            "team-blue-2": teams[4],
            "team-blue-3": teams[5],
        }
        response = requests.post(predictionAPIurl, payload)
        self.input_match_prediction(response.json(), matchID)

    def input_match_prediction(self, returnJson, matchID):
        """

        Takes in json from predictionApi and match_key from TBA
        input_match_prediction Function is used for adding the data from the predictionAPI to redis

        """
        predictionJsonData = self.getPredictionFromJson(
            returnJson
        )  # api code to get prediction
        r.hset(matchID, "predictionAPIPredictedWinner", predictionJsonData[0])
        r.hset(
            matchID, "predictionAPIPredictedWinnerProbability", predictionJsonData[1]
        )

    def update_accuracy(self, matchID):
        """
        
        Takes in match_key Data from TBA
        update_accuracy Function is used to put match predicion data into Redis and to update accuracy of Statbotics. 
        Is called from TBA by match_score notification

        Example Format of info at this time(redis key = 2025wila_sf5m1):
        {   
            'matchID': '2025wila_sf5m1',
            'statboticsPredictedWinner': 'blue',
            'statboticsRedTeamWinningProb': '0.4496',
            'predictionAPIPredictedWinner': 'red',
            'predictionAPIPredictedWinnerProbability': '0.5671841',
            'actualWinner': 'red',
            'wasStatboticsCorrect': 'no',
            'was_prediction_api_correct': 'yes'
        }

        Accuracy Info Example(redis key = predictionApiAccuracy): 
        {
         'numCorrectPredictions': '8',
         'numIncorrectPredictions': '10',
         'predictionApiTotalAccuracy': '0.4444444444444444'
        }

        """

        if (
            r.hget(matchID, "was_prediction_api_correct") is not None
            or r.hget(matchID, "matchID") is None
        ):
            return
        winner = sb.get_match(matchID, ["result"])["result"]["winner"]
        # update the match info to have is_statbotics correct section
        predictionAPIPredictedWinner = r.hget(matchID, "predictionAPIPredictedWinner")
        if (predictionAPIPredictedWinner == "red" and winner == "red") or (
            predictionAPIPredictedWinner == "blue" and winner == "blue"
        ):
            was_prediction_api_correct = "yes"
        else:
            was_prediction_api_correct = "no"
        r.hset(matchID, "was_prediction_api_correct", was_prediction_api_correct)
        # update overall statbotics accuracy
        if r.hgetall("predictionApiAccuracy") == {}:
            r.hset(
                "predictionApiAccuracy",
                mapping={
                    "numCorrectPredictions": 0,
                    "numIncorrectPredictions": 0,
                    "predictionApiTotalAccuracy": 0.0,
                },
            )
        databaseCorrectPredictions = int(
            r.hget("predictionApiAccuracy", "numCorrectPredictions")
        )
        databaseIncorrectPredictions = int(
            r.hget("predictionApiAccuracy", "numIncorrectPredictions")
        )
        if was_prediction_api_correct == "yes":
            databaseCorrectPredictions += 1
            r.hset(
                "predictionApiAccuracy",
                "numCorrectPredictions",
                databaseCorrectPredictions,
            )
        else:
            databaseIncorrectPredictions += 1
            r.hset(
                "predictionApiAccuracy",
                "numIncorrectPredictions",
                databaseIncorrectPredictions,
            )
        newPredictionApiAccuracy = databaseCorrectPredictions / (
            databaseIncorrectPredictions + databaseCorrectPredictions
        )
        r.hset(
            "predictionApiAccuracy",
            "predictionApiTotalAccuracy",
            newPredictionApiAccuracy,
        )

    def getPredictionFromJson(self, input_predictionJsonData):
        """
        
        Takes in prediction json from predictionAPI
        Outputs who the prediction api thinks is going to win: "blue","red", or "draw"

        """

        if (
            input_predictionJsonData["red_alliance_win_confidence"]
            > input_predictionJsonData["blue_alliance_win_confidence"]
        ):
            if (
                input_predictionJsonData["draw_confidence"]
                > input_predictionJsonData["red_alliance_win_confidence"]
            ):
                return ("draw", input_predictionJsonData["draw_confidence"])
            else:
                return ("red", input_predictionJsonData["red_alliance_win_confidence"])
        else:  # blue is more than red
            if (
                input_predictionJsonData["draw_confidence"]
                > input_predictionJsonData["blue_alliance_win_confidence"]
            ):
                return ("draw", input_predictionJsonData["draw_confidence"])
            else:
                return (
                    "blue",
                    input_predictionJsonData["blue_alliance_win_confidence"],
                )