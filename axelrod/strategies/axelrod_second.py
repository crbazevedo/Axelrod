"""
Additional strategies from Axelrod's second tournament.
"""

import random
import numpy as np

from axelrod.action import Action
from axelrod.player import Player
from axelrod.random_ import random_choice

from axelrod.interaction_utils import compute_final_score


C, D = Action.C, Action.D


class Champion(Player):
    """
    Strategy submitted to Axelrod's second tournament by Danny Champion.

    This player cooperates on the first 10 moves and plays Tit for Tat for the
    next 15 more moves. After 25 moves, the program cooperates unless all the
    following are true: the other player defected on the previous move, the
    other player cooperated less than 60% and the random number between 0 and 1
    is greater that the other player's cooperation rate.

    Names:

    - Champion: [Axelrod1980b]_
    """

    name = "Champion"
    classifier = {
        'memory_depth': float('inf'),
        'stochastic': True,
        'makes_use_of': set(),
        'long_run_time': False,
        'inspects_source': False,
        'manipulates_source': False,
        'manipulates_state': False
    }

    def strategy(self, opponent: Player) -> Action:
        current_round = len(self.history)
        # Cooperate for the first 10 turns
        if current_round == 0:
            return C
        if current_round < 10:
            return C
        # Mirror partner for the next phase
        if current_round < 25:
            return opponent.history[-1]
        # Now cooperate unless all of the necessary conditions are true
        defection_prop = opponent.defections / len(opponent.history)
        if opponent.history[-1] == D:
            r = random.random()
            if defection_prop >= max(0.4, r):
                return D
        return C


class Eatherley(Player):
    """
    Strategy submitted to Axelrod's second tournament by Graham Eatherley.

    A player that keeps track of how many times in the game the other player
    defected. After the other player defects, it defects with a probability
    equal to the ratio of the other's total defections to the total moves to
    that point.

    Names:

    - Eatherley: [Axelrod1980b]_
    """

    name = "Eatherley"
    classifier = {
        'memory_depth': float('inf'),
        'stochastic': True,
        'makes_use_of': set(),
        'long_run_time': False,
        'inspects_source': False,
        'manipulates_source': False,
        'manipulates_state': False
    }

    @staticmethod
    def strategy(opponent: Player) -> Action:
        # Cooperate on the first move
        if not len(opponent.history):
            return C
        # Reciprocate cooperation
        if opponent.history[-1] == C:
            return C
        # Respond to defections with probability equal to opponent's total
        # proportion of defections
        defection_prop = opponent.defections / len(opponent.history)
        return random_choice(1 - defection_prop)


class Tester(Player):
    """
    Submitted to Axelrod's second tournament by David Gladstein.

    This strategy is a TFT variant that attempts to exploit certain strategies. It
    defects on the first move. If the opponent ever defects, TESTER 'apologies' by
    cooperating and then plays TFT for the rest of the game. Otherwise TESTER
    alternates cooperation and defection.

    This strategy came 46th in Axelrod's second tournament.

    Names:

    - Tester: [Axelrod1980b]_
    """

    name = "Tester"
    classifier = {
        'memory_depth': float('inf'),
        'stochastic': False,
        'makes_use_of': set(),
        'long_run_time': False,
        'inspects_source': False,
        'manipulates_source': False,
        'manipulates_state': False
    }

    def __init__(self) -> None:
        super().__init__()
        self.is_TFT = False

    def strategy(self, opponent: Player) -> Action:
        # Defect on the first move
        if not opponent.history:
            return D
        # Am I TFT?
        if self.is_TFT:
            return D if opponent.history[-1:] == [D] else C
        else:
            # Did opponent defect?
            if opponent.history[-1] == D:
                self.is_TFT = True
                return C
            if len(self.history) in [1, 2]:
                return C
            # Alternate C and D
            return self.history[-1].flip()


class Gladstein(Player):
    """
    Submitted to Axelrod's second tournament by David Gladstein.

    This strategy is also known as Tester and is based on the reverse
    engineering of the Fortran strategies from Axelrod's second tournament.

    This strategy is a TFT variant that defects on the first round in order to
    test the opponent's response. If the opponent ever defects, the strategy
    'apologizes' by cooperating and then plays TFT for the rest of the game.
    Otherwise, it defects as much as possible subject to the constraint that
    the ratio of its defections to moves remains under 0.5, not counting the
    first defection.

    Names:

    - Gladstein: [Axelrod1980b]_
    - Tester: [Axelrod1980b]_
    """

    name = "Gladstein"
    classifier = {
        'memory_depth': float('inf'),
        'stochastic': False,
        'makes_use_of': set(),
        'long_run_time': False,
        'inspects_source': False,
        'manipulates_source': False,
        'manipulates_state': False
    }

    def __init__(self) -> None:
        super().__init__()
        # This strategy assumes the opponent is a patsy
        self.patsy = True

    def strategy(self, opponent: Player) -> Action:
        # Defect on the first move
        if not self.history:
            return D
        # Is the opponent a patsy?
        if self.patsy:
            # If the opponent defects, apologize and play TFT.
            if opponent.history[-1] == D:
                self.patsy = False
                return C
            # Cooperate as long as the cooperation ratio is below 0.5
            cooperation_ratio = self.cooperations / len(self.history)
            if cooperation_ratio > 0.5:
                return D
            return C
        else:
            # Play TFT
            return opponent.history[-1]


class Tranquilizer(Player):

    """
    Submitted to Axelrod's second tournament by Craig Feathers

    Description given in Axelrod's "More Effective Choice in the
    Prisoner's Dilemma" paper: The rule normally cooperates but
    is ready to defect if the other player defects too often.
    Thus the rule tends to cooperate for the first dozen or two moves
    if the other player is cooperating, but then it throws in a
    defection. If the other player continues to cooperate, then defections
    become more frequent. But as long as Tranquilizer is maintaining an
    average payoff of at least 2.25 points per move, it will never defect
    twice in succession and it will not defect more than
    one-quarter of the time.

    This implementation is based on the reverse engineering of the
    Fortran strategy K67R from Axelrod's second tournament.
    Reversed engineered by: Owen Campbell, Will Guo and Mansour Hakem.

    The strategy starts by cooperating and has 3 states.

    At the start of the strategy it updates its states:

    - It counts the number of consecutive defections by the opponent.
    - If it was in state 2 it moves to state 0 and calculates the
      following quantities two_turns_after_good_defection_ratio and
      two_turns_after_good_defection_ratio_count.

      Formula for:

      two_turns_after_good_defection_ratio:

      self.two_turns_after_good_defection_ratio = (
      ((self.two_turns_after_good_defection_ratio
      * self.two_turns_after_good_defection_ratio_count)
      + (3 - (3 * self.dict[opponent.history[-1]]))
      + (2 * self.dict[self.history[-1]])
      - ((self.dict[opponent.history[-1]]
      * self.dict[self.history[-1]])))
      / (self.two_turns_after_good_defection_ratio_count + 1)
      )

      two_turns_after_good_defection_ratio_count =
      two_turns_after_good_defection_ratio + 1

    - If it was in state 1 it moves to state 2 and calculates the
      following quantities one_turn_after_good_defection_ratio and
      one_turn_after_good_defection_ratio_count.

      Formula for:

      one_turn_after_good_defection_ratio:

      self.one_turn_after_good_defection_ratio = (
      ((self.one_turn_after_good_defection_ratio
      * self.one_turn_after_good_defection_ratio_count)
      + (3 - (3 * self.dict[opponent.history[-1]]))
      + (2 * self.dict[self.history[-1]])
      - (self.dict[opponent.history[-1]]
      * self.dict[self.history[-1]]))
      / (self.one_turn_after_good_defection_ratio_count + 1)
      )

      one_turn_after_good_defection_ratio_count:

      one_turn_after_good_defection_ratio_count =
      one_turn_after_good_defection_ratio + 1

    If after this it is in state 1 or 2 then it cooperates.

    If it is in state 0 it will potentially perform 1 of the 2
    following stochastic tests:

    1. If average score per turn is greater than 2.25 then it calculates a
    value of probability:

    probability = (
    (.95 - (((self.one_turn_after_good_defection_ratio)
    + (self.two_turns_after_good_defection_ratio) - 5) / 15))
    + (1 / (((len(self.history))+1) ** 2))
    - (self.dict[opponent.history[-1]] / 4)
    )

    and will cooperate if a random sampled number is less than that value of
    probability. If it does not cooperate then the strategy moves to state 1
    and defects.

    2. If average score per turn is greater than 1.75 but less than 2.25
    then it calculates a value of probability:

    probability = (
    (.25 + ((opponent.cooperations + 1) / ((len(self.history)) + 1)))
    - (self.opponent_consecutive_defections * .25)
    + ((current_score[0]
    - current_score[1]) / 100)
    + (4 / ((len(self.history)) + 1))
    )

    and will cooperate if a random sampled number is less than that value of
    probability. If not, it defects.

    If none of the above holds the player simply plays tit for tat.

    Tranquilizer came in 27th place in Axelrod's second torunament.


    Names:

    - Tranquilizer: [Axelrod1980]_
    """

    name = 'Tranquilizer'
    classifier = {
        'memory_depth': float('inf'),
        'stochastic': True,
        'makes_use_of': {"game"},
        'long_run_time': False,
        'inspects_source': False,
        'manipulates_source': False,
        'manipulates_state': False
    }

    def __init__(self):
        super().__init__()
        self.num_turns_after_good_defection = 0 # equal to FD variable
        self.opponent_consecutive_defections = 0 # equal to S variable
        self.one_turn_after_good_defection_ratio= 5 # equal to AD variable
        self.two_turns_after_good_defection_ratio= 0 # equal to NO variable
        self.one_turn_after_good_defection_ratio_count = 1 # equal to AK variable
        self.two_turns_after_good_defection_ratio_count = 1 # equal to NK variable
        # All above variables correspond to those in original Fotran Code
        self.dict = {C: 0, D: 1}


    def update_state(self, opponent):

        """
        Calculates the ratio values for the one_turn_after_good_defection_ratio,
        two_turns_after_good_defection_ratio and the probability values,
        and sets the value of num_turns_after_good_defection.
        """
        if opponent.history[-1] == D:
            self.opponent_consecutive_defections += 1
        else:
            self.opponent_consecutive_defections = 0

        if self.num_turns_after_good_defection == 2:
            self.num_turns_after_good_defection = 0
            self.two_turns_after_good_defection_ratio = (
                ((self.two_turns_after_good_defection_ratio
                * self.two_turns_after_good_defection_ratio_count)
                + (3 - (3 * self.dict[opponent.history[-1]]))
                + (2 * self.dict[self.history[-1]])
                - ((self.dict[opponent.history[-1]]
                * self.dict[self.history[-1]])))
                / (self.two_turns_after_good_defection_ratio_count + 1)
                )
            self.two_turns_after_good_defection_ratio_count += 1
        elif self.num_turns_after_good_defection == 1:
            self.num_turns_after_good_defection = 2
            self.one_turn_after_good_defection_ratio = (
                ((self.one_turn_after_good_defection_ratio
                * self.one_turn_after_good_defection_ratio_count)
                + (3 - (3 * self.dict[opponent.history[-1]]))
                + (2 * self.dict[self.history[-1]])
                - (self.dict[opponent.history[-1]]
                * self.dict[self.history[-1]]))
                / (self.one_turn_after_good_defection_ratio_count + 1)
                )
            self.one_turn_after_good_defection_ratio_count += 1

    def strategy(self, opponent: Player) -> Action:

        if not self.history:
            return C


        self.update_state(opponent)
        if  self.num_turns_after_good_defection in [1, 2]:
            return C

        current_score = compute_final_score(zip(self.history, opponent.history))

        if (current_score[0] / ((len(self.history)) + 1)) >= 2.25:
            probability = (
                (.95 - (((self.one_turn_after_good_defection_ratio)
                + (self.two_turns_after_good_defection_ratio) - 5) / 15))
                + (1 / (((len(self.history))+1) ** 2))
                - (self.dict[opponent.history[-1]] / 4)
                )
            if random.random() <= probability:
                return C
            self.num_turns_after_good_defection = 1
            return D
        if (current_score[0] / ((len(self.history)) + 1)) >= 1.75:
            probability = (
                (.25 + ((opponent.cooperations + 1) / ((len(self.history)) + 1)))
                - (self.opponent_consecutive_defections * .25)
                + ((current_score[0]
                - current_score[1]) / 100)
                + (4 / ((len(self.history)) + 1))
                )
            if random.random() <= probability:
                return C
            return D
        return opponent.history[-1]


class MoreGrofman(Player):
    """
    Submitted to Axelrod's second tournament by Bernard Grofman.

    This strategy has 3 phases:

    1. First it cooperates on the first two rounds
    2. For rounds 3-7 inclusive, it plays the same as the opponent's last move
    3. Thereafter, it applies the following logic, looking at its memory of the
       last 8\* rounds (ignoring the most recent round).

      - If its own previous move was C and the opponent has defected less than
        3 times in the last 8\* rounds, cooperate
      - If its own previous move was C and the opponent has defected 3 or
        more times in the last 8\* rounds, defect
      - If its own previous move was D and the opponent has defected only once
        or not at all in the last 8\* rounds, cooperate
      - If its own previous move was D and the opponent has defected more than
        once in the last 8\* rounds, defect

    \* The code looks at the first 7 of the last 8 rounds, ignoring the most
    recent round.

    Names:
    - Grofman's strategy: [Axelrod1980b]_
    - K86R: [Axelrod1980b]_
    """
    name = "MoreGrofman"
    classifier = {
        'memory_depth': 8,
        'stochastic': False,
        'makes_use_of': set(),
        'long_run_time': False,
        'inspects_source': False,
        'manipulates_source': False,
        'manipulates_state': False
    }

    def strategy(self, opponent: Player) -> Action:
        # Cooperate on the first two moves
        if len(self.history) < 2:
            return C
        # For rounds 3-7, play the opponent's last move
        elif 2 <= len(self.history) <= 6:
            return opponent.history[-1]
        else:
            # Note: the Fortran code behavior ignores the opponent behavior
            #   in the last round and instead looks at the first 7 of the last
            #   8 rounds.
            opponent_defections_last_8_rounds = opponent.history[-8:-1].count(D)
            if self.history[-1] == C and opponent_defections_last_8_rounds <= 2:
                return C
            if self.history[-1] == D and opponent_defections_last_8_rounds <= 1:
                return C
            return D


class Kluepfel(Player):
    """
    Strategy submitted to Axelrod's second tournament by Charles Kluepfel
    (K32R).

    This player keeps track of the the opponent's responses to own behavior:

    - `cd_count` counts: Opponent cooperates as response to player defecting.
    - `dd_count` counts: Opponent defects as response to player defecting.
    - `cc_count` counts: Opponent cooperates as response to player cooperating.
    - `dc_count` counts: Opponent defects as response to player cooperating.

    After 26 turns, the player then tries to detect a random player.  The
    player decides that the opponent is random if
    cd_counts >= (cd_counts+dd_counts)/2 - 0.75*sqrt(cd_counts+dd_counts) AND
    cc_counts >= (dc_counts+cc_counts)/2 - 0.75*sqrt(dc_counts+cc_counts).
    If the player decides that they are playing against a random player, then
    they will always defect.

    Otherwise respond to recent history using the following set of rules:

    - If opponent's last three choices are the same, then respond in kind.
    - If opponent's last two choices are the same, then respond in kind with
      probability 90%.
    - Otherwise if opponent's last action was to cooperate, then cooperate
      with probability 70%.
    - Otherwise if opponent's last action was to defect, then defect
      with probability 60%.

    Names:

    - Kluepfel: [Axelrod1980b]_
    """

    name = "Kluepfel"
    classifier = {
        'memory_depth': float('inf'),
        'stochastic': True,
        'makes_use_of': set(),
        'long_run_time': False,
        'inspects_source': False,
        'manipulates_source': False,
        'manipulates_state': False
    }

    def __init__(self):
        super().__init__()
        self.cd_counts, self.dd_counts, self.dc_counts, self.cc_counts = 0, 0, 0, 0

    def strategy(self, opponent: Player) -> Action:
        # First update the response matrix.
        if len(self.history) >= 2:
            if self.history[-2] == D:
                if opponent.history[-1] == C:
                    self.cd_counts += 1
                else:
                    self.dd_counts += 1
            else:
                if opponent.history[-1] == C:
                    self.dc_counts += 1
                else:
                    self.cc_counts += 1

        # Check for randomness
        if len(self.history) > 26:
            if self.cd_counts >= (self.cd_counts+self.dd_counts)/2 - 0.75*np.sqrt(self.cd_counts+self.dd_counts) and \
                self.cc_counts >= (self.dc_counts+self.cc_counts)/2 - 0.75*np.sqrt(self.dc_counts+self.cc_counts):
                return D

        # Otherwise respond to recent history

        one_move_ago, two_moves_ago, three_moves_ago = C, C, C
        if len(opponent.history) >= 1:
            one_move_ago = opponent.history[-1]
        if len(opponent.history) >= 2:
            two_moves_ago = opponent.history[-2]
        if len(opponent.history) >= 3:
            three_moves_ago = opponent.history[-3]

        if one_move_ago == two_moves_ago and two_moves_ago == three_moves_ago:
            return one_move_ago

        r = random.random() # Everything following is stochastic
        if one_move_ago == two_moves_ago:
            if r < 0.9:
                return one_move_ago
            else:
                return one_move_ago.flip()
        if one_move_ago == C:
            if r < 0.7:
                return one_move_ago
            else:
                return one_move_ago.flip()
        if one_move_ago == D:
            if r < 0.6:
                return one_move_ago
            else:
                return one_move_ago.flip()


class Borufsen(Player):
    """
    Strategy submitted to Axelrod's second tournament by Otto Borufsen
    (K32R), and came in third in that tournament.

    This player keeps track of the the opponent's responses to own behavior:

    - `cd_count` counts: Opponent cooperates as response to player defecting.
    - `cc_count` counts: Opponent cooperates as response to player cooperating.

    The player has a defect mode and a normal mode.  In defect mode, the
    player will always defect.  In normal mode, the player obeys the following
    ranked rules:

    1. If in the last three turns, both the player/opponent defected, then
       cooperate for a single turn.
    2. If in the last three turns, the player/opponent acted differently from
       each other and they're alternating, then change next defect to
       cooperate.  (Doesn't block third rule.)
    3. Otherwise, do tit-for-tat.

    Start in normal mode, but every 25 turns starting with the 27th turn,
    re-evaluate the mode.  Enter defect mode if any of the following
    conditions hold:

    - Detected random:  Opponent cooperated 7-18 times since last mode
      evaluation (or start) AND less than 70% of opponent cooperation was in
      response to player's cooperation, i.e.
      cc_count / (cc_count+cd_count) < 0.7
    - Detect defective:  Opponent cooperated fewer than 3 times since last mode
      evaluation.

    When switching to defect mode, defect immediately.  The first two rules for
    normal mode require that last three turns were in normal mode.  When starting
    normal mode from defect mode, defect on first move.

    Names:

    - Borufsen: [Axelrod1980b]_
    """

    name = "Borufsen"
    classifier = {
        'memory_depth': float('inf'),
        'stochastic': False,
        'makes_use_of': set(),
        'long_run_time': False,
        'inspects_source': False,
        'manipulates_source': False,
        'manipulates_state': False
    }

    def __init__(self):
        super().__init__()
        self.cd_counts, self.cc_counts = 0, 0
        self.mutual_defect_streak = 0
        self.echo_streak = 0
        self.flip_next_defect = False
        self.mode = "Normal"

    def try_return(self, to_return):
        """
        We put the logic here to check for the `flip_next_defect` bit here,
        and proceed like normal otherwise.
        """

        if to_return == C:
            return C
        # Otherwise look for flip bit.
        if self.flip_next_defect:
            self.flip_next_defect = False
            return C
        return D

    def strategy(self, opponent: Player) -> Action:
        turn = len(self.history) + 1

        if turn == 1:
            return C

        # Update the response history.
        if turn >= 3:
            if opponent.history[-1] == C:
                if self.history[-2] == C:
                    self.cc_counts += 1
                else:
                    self.cd_counts += 1

        # Check if it's time for a mode change.
        if turn > 2 and turn % 25 == 2:
            coming_from_defect = False
            if self.mode == "Defect":
                coming_from_defect = True

            self.mode = "Normal"
            coops = self.cd_counts + self.cc_counts

            # Check for a defective strategy
            if coops < 3:
                self.mode = "Defect"

            # Check for a random strategy
            if (coops >= 8 and coops <= 17) and self.cc_counts/coops < 0.7:
                self.mode = "Defect"

            self.cd_counts, self.cc_counts = 0, 0

            # If defect mode, clear flags
            if self.mode == "Defect":
                self.mutual_defect_streak = 0
                self.echo_streak = 0
                self.flip_next_defect = False

            # Check this special case
            if self.mode == "Normal" and coming_from_defect:
                return D

        # Proceed
        if self.mode == "Defect":
            return D
        else:
            assert self.mode == "Normal"

            # Look for mutual defects
            if self.history[-1] == D and opponent.history[-1] == D:
                self.mutual_defect_streak += 1
            else:
                self.mutual_defect_streak = 0
            if self.mutual_defect_streak >= 3:
                self.mutual_defect_streak = 0
                self.echo_streak = 0 # Reset both streaks.
                return self.try_return(C)

            # Look for echoes
            # Fortran code defaults two turns back to C if only second turn
            my_two_back, opp_two_back = C, C
            if turn >= 3:
                my_two_back = self.history[-2]
                opp_two_back = opponent.history[-2]
            if self.history[-1] != opponent.history[-1] and \
                self.history[-1] == opp_two_back and opponent.history[-1] == my_two_back:
                self.echo_streak += 1
            else:
                self.echo_streak = 0
            if self.echo_streak >= 3:
                self.mutual_defect_streak = 0 # Reset both streaks.
                self.echo_streak = 0
                self.flip_next_defect = True

            # Tit-for-tat
            return self.try_return(opponent.history[-1])


class Cave(Player):
    """
    Strategy submitted to Axelrod's second tournament by Rob Cave (K49R), and
    came in fourth in that tournament.

    First look for overly-defective or apparently random opponents, and defect
    if found.  That is any opponent meeting one of:

    - turn > 39 and percent defects > 0.39
    - turn > 29 and percent defects > 0.65
    - turn > 19 and percent defects > 0.79

    Otherwise, respond to cooperation with cooperation.  And respond to defcts
    with either a defect (if opponent has defected at least 18 times) or with
    a random (50/50) choice.  [Cooperate on first.]

    Names:

    - Cave: [Axelrod1980b]_
    """

    name = "Cave"
    classifier = {
        'memory_depth': float('inf'),
        'stochastic': True,
        'makes_use_of': set(),
        'long_run_time': False,
        'inspects_source': False,
        'manipulates_source': False,
        'manipulates_state': False
    }

    def strategy(self, opponent: Player) -> Action:
        turn = len(self.history) + 1
        if turn == 1:
            return C

        number_defects = opponent.defections
        perc_defects = number_defects / turn

        # Defect if the opponent has defected often or appears random.
        if turn > 39 and perc_defects > 0.39:
            return D
        if turn > 29 and perc_defects > 0.65:
            return D
        if turn > 19 and perc_defects > 0.79:
            return D

        if opponent.history[-1] == D:
            if number_defects > 17:
                return D
            else:
                return random_choice(0.5)
        else:
            return C


class WmAdams(Player):
    """
    Strategy submitted to Axelrod's second tournament by William Adams (K44R),
    and came in fifth in that tournament.

    Count the number of opponent defections after their first move, call
    `c_defect`.  Defect if c_defect equals 4, 7, or 9.  If c_defect > 9,
    then defect immediately after opponent defects with probability =
    (0.5)^(c_defect-1).  Otherwise cooperate.

    Names:

    - WmAdams: [Axelrod1980b]_
    """

    name = "WmAdams"
    classifier = {
        'memory_depth': float('inf'),
        'stochastic': True,
        'makes_use_of': set(),
        'long_run_time': False,
        'inspects_source': False,
        'manipulates_source': False,
        'manipulates_state': False
    }

    def strategy(self, opponent: Player) -> Action:
        if len(self.history) <= 1:
            return C
        number_defects = opponent.defections
        if opponent.history[0] == D:
            number_defects -= 1

        if number_defects in [4, 7, 9]:
            return D
        if number_defects > 9 and opponent.history[-1] == D:
            return random_choice((0.5) ** (number_defects - 9))
        return C


class GraaskampKatzen(Player):
    """
    Strategy submitted to Axelrod's second tournament by Jim Graaskamp and Ken
    Katzen (K60R), and came in sixth in that tournament.

    Play Tit-for-Tat at first, and track own score.  At select checkpoints,
    check for a high score.  Switch to Default Mode if:

    - On move 11, score < 23
    - On move 21, score < 53
    - On move 31, score < 83
    - On move 41, score < 113
    - On move 51, score < 143
    - On move 101, score < 293

    Once in Defect Mode, defect forever.

    Names:

    - GraaskampKatzen: [Axelrod1980b]_
    """

    name = "GraaskampKatzen"
    classifier = {
        'memory_depth': float('inf'),
        'stochastic': False,
        'makes_use_of': set(['game']),
        'long_run_time': False,
        'inspects_source': False,
        'manipulates_source': False,
        'manipulates_state': False
    }

    def __init__(self):
        super().__init__()
        self.own_score = 0
        self.mode = "Normal"

    def update_score(self, opponent: Player):
        game = self.match_attributes["game"]
        last_round = (self.history[-1], opponent.history[-1])
        self.own_score += game.score(last_round)[0]

    def strategy(self, opponent: Player) -> Action:
        if self.mode == "Defect":
            return D

        turn = len(self.history) + 1
        if turn == 1:
            return C

        self.update_score(opponent)

        if turn == 11 and self.own_score < 23 or \
           turn == 21 and self.own_score < 53 or \
           turn == 31 and self.own_score < 83 or \
           turn == 41 and self.own_score < 113 or \
           turn == 51 and self.own_score < 143 or \
           turn == 101 and self.own_score < 293:
            self.mode = "Defect"
            return D

        return opponent.history[-1] # Tit-for-Tat


class Weiner(Player):
    """
    Strategy submitted to Axelrod's second tournament by Herb Weiner (K41R),
    and came in seventh in that tournament.

    Play Tit-for-Tat with a chance for forgiveness and a defective override.

    The chance for forgiveness happens only if `forgive_flag` is raised
    (flag discussed below).  If raised and `turn` is greater than `grudge`,
    then override Tit-for-Tat with Cooperation.  `grudge` is a variable that
    starts at 0 and increments 20 with each forgiven Defect (a Defect that is
    overriden through the forgiveness logic).  `forgive_flag` is lower whether
    logic is overriden or not.

    The variable `defect_padding` increments with each opponent Defect, but
    resets to zero with each opponent Cooperate (or `forgive_flag` lowering) so
    that it roughly counts Defects between Cooperates.  Whenever the opponent
    Cooperates, if `defect_padding` (before reseting) is odd, then we raise
    `forgive_flag` for next turn.

    Finally a defective override is assessed after forgiveness.  If five or
    more of the opponent's last twelve actions are Defects, then Defect.  This
    will overrule a forgiveness, but doesn't undo the lowering of
    `forgiveness_flag`.  Note that "last twelve actions" doesn't count the most
    recent action.  Actually the original code updates history after checking
    for defect override.

    Names:

    - Weiner: [Axelrod1980b]_
    """

    name = "Weiner"
    classifier = {
        'memory_depth': float('inf'),
        'stochastic': False,
        'makes_use_of': set(),
        'long_run_time': False,
        'inspects_source': False,
        'manipulates_source': False,
        'manipulates_state': False
    }

    def __init__(self):
        super().__init__()
        self.forgive_flag = False
        self.grudge = 0
        self.defect_padding = 0
        self.last_twelve = [0] * 12
        self.lt_index = 0 # Circles around last_twelve

    def try_return(self, to_return):
        """
        We put the logic here to check for the defective override.
        """

        if np.sum(self.last_twelve) >= 5:
            return D
        return to_return

    def strategy(self, opponent: Player) -> Action:
        if len(opponent.history) == 0:
            return C

        # Update history, lag 1.
        if len(opponent.history) >= 2:
            self.last_twelve[self.lt_index] = 0
            if opponent.history[-2] == D:
                self.last_twelve[self.lt_index] = 1
            self.lt_index = (self.lt_index + 1) % 12

        if self.forgive_flag:
            self.forgive_flag = False
            self.defect_padding = 0
            if self.grudge < len(self.history) + 1 and opponent.history[-1] == D:
                # Then override
                self.grudge += 20
                return self.try_return(C)
            else:
                return self.try_return(opponent.history[-1])
        else:
            # See if forgive_flag should be raised
            if opponent.history[-1] == D:
                self.defect_padding += 1
            else:
                if self.defect_padding % 2 == 1:
                    self.forgive_flag = True
                self.defect_padding = 0

            return self.try_return(opponent.history[-1])


class Harrington(Player):
    """
    Strategy submitted to Axelrod's second tournament by Paul Harrington (K75R)
    and came in eighth in that tournament.

    This strategy has three modes:  Normal, Fair-weather, and Defect.  These
    mode names were not present in Harrington's submission.

    In Normal and Fair-weather modes, the strategy begins by:

    - Update history
    - Detects random if turn is multiple of 15 and >=30.
    - Check if `burned` flag should be raised.
    - Check for Fair-weather opponent if turn is 38.

    Updating history means to increment the correct cell of the `move_history`.
    `move_history` is a matrix where the columns are the opponent's previous
    move and rows are indexed by the combo of this player and the opponent's
    moves two turns ago*.  [The upper-left cell must be all cooperations, but
    otherwise order doesn't matter.]   * If the player is exiting Defect mode,
    then the history to determine the row is taken from before the turn that
    the player entered Defect mode.  (That is, the turn that started in Normal
    mode, but ended in Defect mode.)

    If the turn is a multiple of 15 and >=30, then attempt to detect random.
    If random is detected, enter Defect mode and defect immediately.  If the
    player was previously in Defect mode, then do not re-enter.  The random
    detection logic is a modified Pearson's Chi Squared test, with some
    additional checks.  [More details in `detect_random` docstrings.]

    Some of this player's moves are marked as "generous."  If this player made
    a generous move two turns ago and the opponent replied with a Defect, then
    raise the `burned` flag.  This will stop certain generous moves later.

    The player mostly plays Tit-for-Tat for the first 36 moves, then defects on
    the 37th move.  If the opponent cooperates on the first 36 moves, and
    defects on the 37th move also, then enter Fair-weather mode and cooperate
    this turn.  Entering Fair-weather mode is extremely rare, since this can
    only happen if the opponent cooperates for the first 36 then defects
    unprovoked on the 37th.  (That is, this player's first 36 moves are also
    Cooperations, so there's nothing really to trigger an opponent Defection.)

    Next in Normal Mode:

    1. Check for defect and parity streaks.
    2. Check if cooperations are scheduled.
    3. Otherwise,

    - If turn < 37, Tit-for-Tat.
    - If turn = 37, defect, mark this move as generous, and schedule two
      more cooperations**.
    - If turn > 37, then if `burned` flag is raised, then Tit-for-Tat.
      Otherwise, Tit-for-Tat with probability 1 - `prob`.  And with
      probability `prob`, defect, schedule two cooperations, mark this move
      as generous, and increase `prob` by 5%.

    ** Scheduling two cooperations means to set `more_coop` flag to two.  If in
    Normal mode and no streaks are detected, then the player will cooperate and
    lower this flag, until hitting zero.  It's possible that the flag can be
    overwritten.  Notable on the 37th turn defect, this is set to two, but the
    38th turn Fair-weather check will set this.

    If the opponent's last twenty moves were defections, then defect this turn.
    Then check for a parity streak, by flipping the parity bit (there are two
    streaks that get tracked which are something like odd and even turns, but
    this flip bit logic doesn't get run every turn), then incrementing the
    parity streak that we're pointing to.  If the parity streak that we're
    pointing to is then greater than `parity_limit` then reset the streak and
    cooperate immediately.  `parity_limit` is initially set to five, but after
    its been hit eight times, it decreases to three.  The parity streak that
    we're pointing to also gets incremented if in normal mode and WE defect but
    not on turn 38, unless the result of a defect streak.  Note that the parity
    streaks reset but the defect streak doesn't.

    If `more_coop` >= 1, then we cooperate and lower that flag here, in Normal
    mode after checking streaks.  Still lower this flag if cooperating as the
    result of a parity streak or in Fair-weather mode.

    Then use the logic based on turn from above.

    In Fair-Weather mode after running the code from above, check if opponent
    defected last turn.  If so, exit Fair-Weather mode, and proceed THIS TURN
    with Normal mode.  Otherwise cooperate.

    In Defect mode, update the `exit_defect_meter` (originally zero) by
    incrementing if opponent defected last turn and decreasing by three
    otherwise.  If `exit_defect_meter` is then 11, then set mode to Normal (for
    future turns), cooperate and schedule two more cooperations.  [Note that
    this move is not marked generous.]

    Names:

    - Harrington: [Axelrod1980b]_
    """

    name = "Harrington"
    classifier = {
        'memory_depth': float('inf'),
        'stochastic': True,
        'makes_use_of': set(),
        'long_run_time': False,
        'inspects_source': False,
        'manipulates_source': False,
        'manipulates_state': False
    }

    def __init__(self):
        super().__init__()
        self.mode = "Normal"
        self.recorded_defects = 0
        self.exit_defect_meter = 0
        self.coops_in_first_36 = None
        self.was_defective = False

        self.prob = 0.25

        self.move_history = np.zeros([4, 2])
        self.history_row = 0

        self.more_coop = 0
        self.generous_n_turns_ago = 3
        self.burned = False

        self.defect_streak = 0
        self.parity_streak = [0, 0]
        self.parity_bit = 0
        self.parity_limit = 5
        self.parity_hits = 0

    def try_return(self, to_return, lower_flags=True, inc_parity=False):
        if lower_flags and to_return == C:
            self.more_coop -= 1
            self.generous_n_turns_ago += 1

        if inc_parity and to_return == D:
            self.parity_streak[self.parity_bit] += 1

        return to_return

    def detect_random(self, turn):
        """
        Calculates a modified Pearson's Chi Squared statistic on self.history,
        and returns True (is random) if and only if the statistic is less than
        or equal to 3.

        Pearson's Chi Squared statistic = sum[ (E_i-O_i)^2 / E_i ], where O_i
        are the observed matrix values, and E_i is calculated as number (of
        defects) in the row times the number in the column over (total number
        in the matrix minus 1).

        We say this is modified because it differs from a usual Chi-Squared
        test in that:

        - It divides by turns minus 2 to get expected, whereas usually we'd
          divide by matrix total.  Total equals turns minus 1, unless Defect
          mode has been entered at any point.
        - Terms where expected counts are less than 1 get excluded.
        - There's a check at the beginning on the first cell of the matrix.
        - There's a check at the beginning for the recorded number of defects.

        """
        denom = turn - 2

        if self.move_history[0, 0] / denom >= 0.8:
            return False
        if self.recorded_defects / denom < 0.25 or self.recorded_defects / denom > 0.75:
            return False

        expected_matrix = np.outer(self.move_history.sum(axis=1), \
                                    self.move_history.sum(axis=0))

        chi_squared = 0.0
        for i in range(4):
            for j in range(2):
                expct = expected_matrix[i, j] / denom
                if expct > 1.0:
                    chi_squared += (expct - self.move_history[i, j]) ** 2 / expct

        if chi_squared > 3:
            return False
        return True

    def detect_streak(self, last_move):
        """
        Return if and only if the opponent's last twenty moves are defects.
        """

        if last_move == D:
            self.defect_streak += 1
        else:
            self.defect_streak = 0
        if self.defect_streak >= 20:
            return True
        return False

    def detect_parity_streak(self, last_move):
        self.parity_bit = 1 - self.parity_bit # Flip bit
        if last_move == D:
            self.parity_streak[self.parity_bit] += 1
        else:
            self.parity_streak[self.parity_bit] = 0
        if self.parity_streak[self.parity_bit] >= self.parity_limit:
            return True

    def strategy(self, opponent: Player) -> Action:
        turn = len(self.history) + 1

        if turn == 1:
            return C

        if self.mode == "Defect":
            if opponent.history[-1] == D:
                self.exit_defect_meter += 1
            else:
                self.exit_defect_meter -= 3
            if self.exit_defect_meter >= 11:
                self.mode = "Normal"
                self.was_defective = True
                self.more_coop = 2
                return self.try_return(to_return=C, lower_flags=False)

            return self.try_return(D)


        # If not Defect mode, proceed to update history and check for random,
        # check if burned, and check if opponent's fairweather.

        # History only gets updated outside of Defect mode.
        if turn > 2:
            if opponent.history[-1] == D:
                self.recorded_defects += 1
            opp_col = 1 if opponent.history[-1] == D else 0
            self.move_history[self.history_row, opp_col] += 1

        # Detect random
        if turn % 15 == 0 and turn > 15 and not self.was_defective:
            if self.detect_random(turn):
                self.mode = "Defect"
                return self.try_return(D, lower_flags=False) # Lower_flags not used here.

        # history_row only gets updated if not in Defect mode AND not entering
        # Defect mode.
        self.history_row = 1 if opponent.history[-1] == D else 0
        if self.history[-1] == D:
            self.history_row += 2

        # If generous 2 turn ago and opponent defected last turn
        if self.generous_n_turns_ago == 2 and opponent.history[-1] == D:
            self.burned = True

        if turn == 38 and opponent.history[-1] == D and opponent.cooperations == 36:
            self.mode = "Fair-weather"
            return self.try_return(to_return=C, lower_flags=False)


        if self.mode == "Fair-weather":
            if opponent.history[-1] == D:
                self.mode = "Normal" # Post-Defect is not possible
                #Continue below
            else:
                # Never defect against a fair-weather opponent
                return self.try_return(C)

        # Continue with Normal mode

        # Check for streaks
        if self.detect_streak(opponent.history[-1]):
            return self.try_return(D, inc_parity=True)
        if self.detect_parity_streak(opponent.history[-1]):
            self.parity_streak[self.parity_bit] = 0
            self.parity_hits += 1
            if self.parity_hits >= 8:
                self.parity_limit = 3
            return self.try_return(C, inc_parity=True) # Inc parity won't get used here.

        if self.more_coop >= 1:
            return self.try_return(C, inc_parity=True)

        if turn < 37:
            return self.try_return(opponent.history[-1], inc_parity=True)
        if turn == 37:
            self.more_coop, self.generous_n_turns_ago = 2, 1
            return self.try_return(D, lower_flags=False)
        if self.burned or random.random() > self.prob:
            return self.try_return(opponent.history[-1], inc_parity=True)
        else:
            self.prob += 0.05
            self.more_coop, self.generous_n_turns_ago = 2, 1
            return self.try_return(D, lower_flags=False)
