import typing


class Observable:
    """
    Class used to publish intermediate results of the detectors.
    """

    def __init__(self):
        self.published_events = {}

    def add_observer(self, event: str, observer: typing.Callable):
        if event in self.published_events:
            self.published_events[event].append(observer)
        else:
            self.published_events[event] = [observer]

    def publish(self, event: str, **attrs):
        if event in self.published_events:
            for observer in self.published_events[event]:
                observer(**attrs)
