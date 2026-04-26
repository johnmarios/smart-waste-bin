from typing import Optional, List, Dict

class PirInterpreter:
    # min high duration and cooldown logic:
    # - When we see a rising edge (LOW->HIGH), we record the time it went HIGH and reset the "emitted for this HIGH" flag.
    # - When we see a falling edge (HIGH->LOW), we clear the "high start time" and reset the "emitted for this HIGH" flag.
    # - On every update, if the signal is currently HIGH and we haven't emitted for this HIGH period, we check how long it's been HIGH. 
    # If it's been HIGH for at least min_high_s, we then check if we're in cooldown (i.e., if the time since last emit is less than cooldown_s).
    # If we're not in cooldown, we emit a motion_detected event and set the "emitted for this HIGH" flag to True and record the last emit time.
    def __init__(self, cooldown_s: float = 0.0, min_high_s: float = 0.0):
        # cooldown_s: minimum time between emitted events (debounce)
        # min_high_s: minimum time the signal must be HIGH before we emit an event
        self.cooldown_s = cooldown_s
        self.min_high_s = min_high_s

        # Internal state
        self.prev_raw = False # Assume starting LOW
        # Optional[float] because it can be None if we haven't seen a HIGH yet
        # so we initialize it to None and set it to a timestamp when we see a rising edge
        self.high_start_t: Optional[float] = None # When the signal went HIGH
        self.emitted_for_this_high = False # Have we emitted an event for the current HIGH period?
        self.last_emit_t: Optional[float] = None # When we last emitted an event (for cooldown)

    def update(self, raw: bool, t: float) -> List[Dict]:
        '''Process a new raw reading at time t and return a list of events (possibly empty).'''
        events: List[Dict] = [] # List of events to return

        # rising:low->high
        rising = (not self.prev_raw) and raw # HIGH (when previous was LOW) and HIGH = enabled 
        # falling:high->low
        falling = self.prev_raw and (not raw) # LOW (when previous was HIGH) and HIGH = enabled

        if rising:
            self.high_start_t = t
            self.emitted_for_this_high = False

        if falling:
            self.high_start_t = None
            self.emitted_for_this_high = False

        # If currently HIGH and we haven't emitted yet, check min_high and cooldown
        if raw and (not self.emitted_for_this_high) and (self.high_start_t is not None):
            high_for = t - self.high_start_t # How long has it been HIGH?
            if high_for >= self.min_high_s: # Check if it meets the minimum HIGH duration
                in_cd = self.last_emit_t is not None and (t - self.last_emit_t) < self.cooldown_s # Check if we're in cooldown
                if not in_cd: # if not in cooldown, emit event
                    events.append({"kind": "motion_detected", "t": t})
                    self.last_emit_t = t
                    self.emitted_for_this_high = True

        self.prev_raw = raw # high or low for the next update
        return events