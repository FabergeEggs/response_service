from abc import ABC, abstractmethod


class ResponseServiceBase(ABC):
    @abstractmethod
    def who_i_am(self):
        pass
