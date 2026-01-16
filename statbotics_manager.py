import redis
import statbotics

r = redis.Redis(host="192.168.100.2", port=6379, decode_responses=True)
sb = statbotics.Statbotics()

class Statbotics_Manager:
    def __init__(self):
        pass

    def get_EPA(self, team):
        """Get EPA of team"""
        try:
            data = sb.get_team(team)
            print(data["norm_epa"]["current"])
        except UserWarning:
            print("not found")

    def fetch_prediction(self, matchID):  
        """
        Takes in match_key from TBA
        fetch_prediction Function is used for average predictions. Gets probability of red winning for a match and returns it in a tuple
        Tuple Format: (winnerPredict, red is winner probability, totalAccuracy), if match does not exist, return None

        """
        if r.hexists(matchID, "statboticsRedTeamWinningProb"):
            winProbability = r.hget(matchID, "statboticsRedTeamWinningProb")
            return (
                r.hget(matchID, "statboticsPredictedWinner"),
                winProbability,
                r.hget("statboticsAccuracy", "statboticsTotalAccuracy"),
            )
        else:
            return None

    def calculate_match_prediction(self, matchID):
        """
        
        Takes in match_key from TBA
        calculate_match_prediction Function is used to put initial match prediction data into Redis. 
        Is called from TBA by upcoming_match notification
        
        Example Format of Info at this time:
        Example Format of info:
        {   
            'matchID': '2025wila_sf5m1',
            'statboticsPredictedWinner': 'blue',
            'statboticsRedTeamWinningProb': '0.4496',
            'predictionAPIPredictedWinner': 'red',
            'predictionAPIPredictedWinnerProbability': '0.5671841',
        }

        """
        if r.hget(matchID, "matchID") is not None:
            return
        redTeamWinningProb = float(
            sb.get_match(matchID, ["pred"])["pred"]["red_win_prob"]
        )
        predictedWinner = ""
        # get winning probability
        if redTeamWinningProb >= 0.5:
            predictedWinner = "red"
        else:
            predictedWinner = "blue"
        r.hset(
            matchID,
            mapping={
                "matchID": matchID,
                "statboticsPredictedWinner": predictedWinner,
                "statboticsRedTeamWinningProb": redTeamWinningProb,
            },
        )

    def update_accuracy(self, match_data):
        """
        
        Takes in Match Data from TBA
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
        # if the acuracy was already checked, return early as accuracy should not be checked again
        matchID = match_data["match_key"]
        if (
            r.hget(matchID, "wasStatboticsCorrect") is not None
            or r.hget(matchID, "matchID") is None
        ):
            return
        # find and update winner
        winner = sb.get_match(matchID, ["result"])["result"]["winner"]
        r.hset(matchID, "actualWinner", winner)
        # update the match info to have is_statbotics correct section
        redTeamWinningProb = r.hget(matchID, "statboticsRedTeamWinningProb")
        if (float(redTeamWinningProb) >= 0.5 and winner == "red") or (
            float(redTeamWinningProb) <= 0.5 and winner == "blue"
        ):
            wasStatboticsCorrect = "yes"
        else:
            wasStatboticsCorrect = "no"
        r.hset(matchID, "wasStatboticsCorrect", wasStatboticsCorrect)

        # update overall statbotics accuracy
        if r.hgetall("statboticsAccuracy") == {}:
            r.hset(
                "statboticsAccuracy",
                mapping={
                    "numCorrectPredictions": 0,
                    "numIncorrectPredictions": 0,
                    "statboticsTotalAccuracy": 0.0,
                },
            )
        databaseCorrectPredictions = int(
            r.hget("statboticsAccuracy", "numCorrectPredictions")
        )
        databaseIncorrectPredictions = int(
            r.hget("statboticsAccuracy", "numIncorrectPredictions")
        )
        if wasStatboticsCorrect == "yes":
            databaseCorrectPredictions += 1
            r.hset(
                "statboticsAccuracy",
                "numCorrectPredictions",
                databaseCorrectPredictions,
            )
        else:
            databaseIncorrectPredictions += 1
            r.hset(
                "statboticsAccuracy",
                "numIncorrectPredictions",
                databaseIncorrectPredictions,
            )
        newStatboticsTotalAccuracy = databaseCorrectPredictions / (
            databaseIncorrectPredictions + databaseCorrectPredictions
        )
        r.hset(
            "statboticsAccuracy", "statboticsTotalAccuracy", newStatboticsTotalAccuracy
        )

        #add all data from statbotics for that match
        self.add_complete_data(matchID)

    def add_complete_data(self, matchID):
        r.hset(matchID, "complete_statbotics_data", sb.get_match(matchID))