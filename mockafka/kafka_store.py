"""
mock_topics = {
    'sample_topic':{
        1: [],
        2: [],
        3: [],
        4: []
    }
}

offset_store = {
    'sample_topic_1': {
        'first_offset': 0,
        'next_offset': 0,
    }
}
"""
from confluent_kafka import KafkaException
from .message import Message

mock_topics: dict[str, dict[int, list[Message]]] = {}

offset_store: dict[str, dict[str, int]] = {}

NEW_OFFSET = {
    'first_offset': 0,
    'next_offset': 0
}


class KafkaStore:
    """
    In memory kafka store
    """
    FIRST_OFFSET = 'first_offset'
    NEXT_OFFSET = 'next_offset'

    @staticmethod
    def is_topic_exist(topic: str) -> bool:
        return topic in mock_topics.keys()

    @classmethod
    def is_partition_exist_on_topic(cls, topic: str, partition_num: int) -> bool:
        if not cls.is_topic_exist(topic=topic):
            raise KafkaException('Topic Does not exist')

        return mock_topics[topic].get(partition_num, None) is not None

    @staticmethod
    def get_number_of_partition(topic: str) -> int:
        return len(mock_topics[topic].keys())

    @staticmethod
    def create_topic(topic: str):
        if mock_topics.get(topic, None) is None:
            raise KafkaException(f'{topic} exist is fake kafka')

        mock_topics[topic] = {}

    def create_partition(self, topic: str, partitions: int):
        if not self.is_topic_exist(topic=topic):
            self.create_topic(topic=topic)

        len_of_current_partition = len(mock_topics[topic].keys())
        if partitions >= len_of_current_partition:
            for i in range(len_of_current_partition, partitions):
                mock_topics[topic][i] = []
                offset_store[self.get_offset_store_key(topic, i)] = NEW_OFFSET

        else:
            raise KafkaException('can not decrease partition of topic')

    def remove_topic(self, topic: str):
        mock_topics.pop(topic)
        for offset_key in offset_store.keys():
            if topic in offset_key:
                offset_store.pop(offset_key)

    def set_first_offset(self, topic: str, partition: int, value: int):
        offset_store_key = self.get_offset_store_key(topic=topic, partition=partition)
        first_offset = self.get_partition_first_offset(topic=topic, partition=partition)
        next_offset = self.get_partition_next_offset(topic=topic, partition=partition)

        if first_offset < value < next_offset:
            offset_store[offset_store_key][self.FIRST_OFFSET] = value

    def _add_next_offset(self, topic: str, partition: int):
        offset_store_key = self.get_offset_store_key(topic=topic, partition=partition)
        offset_store[offset_store_key][self.NEXT_OFFSET] += 1

    def get_offset_store_key(self, topic: str, partition: int):
        return f'{topic}*{partition}'

    def produce(self, message: Message, topic: str, partition: int):
        if not self.is_topic_exist(topic=topic):
            raise KafkaException(f'can not produce on {topic}, Topic Does Not Exist')

        if mock_topics[topic].get(partition, None) is None:
            raise KafkaException(f'can not produce on partition {partition} of {topic}, partition does not exist')

        if not partition:
            raise KafkaException('you must assigne partition when you want to produce message')

        # add message to topic
        mock_topics[topic][partition].append(message)

        self._add_next_offset(topic=topic, partition=partition)

    def get_message(self, topic: str, partition: int, offset: int) -> Message:
        return self.get_messages_in_partition(topic=topic, partition=partition)[offset]

    def get_partition_first_offset(self, topic: str, partition: int) -> int:
        offset_store_key = self.get_offset_store_key(topic=topic, partition=partition)
        return offset_store[offset_store_key][self.FIRST_OFFSET]

    def get_partition_next_offset(self, topic: str, partition: int) -> int:
        offset_store_key = self.get_offset_store_key(topic=topic, partition=partition)
        return offset_store[offset_store_key][self.NEXT_OFFSET]

    @staticmethod
    def topic_list() -> list[str]:
        return list(mock_topics.keys())

    @staticmethod
    def partition_list(topic: str) -> list[int]:
        return list(mock_topics[topic].keys())

    @staticmethod
    def get_messages_in_partition(topic: str, partition: int) -> list[Message]:
        return mock_topics[topic][partition]

    def number_of_message_in_topic(self, topic: str) -> int:
        count_of_messages = 0
        for partition in self.partition_list(topic=topic):
            count_of_messages += len(self.get_messages_in_partition(topic=topic, partition=partition))

        return count_of_messages

    def clear_topic_messages(self, topic: str):
        for partition in self.partition_list(topic=topic):
            self.clear_partition_messages(topic=topic, partition=partition)

    @staticmethod
    def clear_partition_messages(topic: str, partition: int):
        mock_topics[topic][partition] = []

    def reset_offset(self, topic: str, strategy: str = 'latest'):
        for partition in self.partition_list(topic=topic):
            key = self.get_offset_store_key(topic, partition)

            if strategy == 'latest':
                offset_store[key][self.FIRST_OFFSET] = offset_store[key][self.NEXT_OFFSET]

            elif strategy == 'earliest':
                offset_store[key][self.FIRST_OFFSET] = 0