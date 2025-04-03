import csv
import time
from abc import ABC, abstractmethod
from typing import List, Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class Order:
    id: int
    type: str
    amount: float
    flag: bool
    status: str = 'new'
    priority: str = 'low'


@dataclass
class APIResponse:
    status: str
    data: Any


class APIException(Exception):
    pass


class DatabaseException(Exception):
    pass


class DatabaseService(ABC):
    @abstractmethod
    def get_orders_by_user(self, user_id: int) -> List[Order]:
        """ pass """

    @abstractmethod
    def update_order_status(self, order_id: int, status: str, priority: str) -> bool:
        """ pass """


class APIClient(ABC):
    @abstractmethod
    def call_api(self, order_id: int) -> APIResponse:
        """ pass """


class FileWriter(ABC):
    @abstractmethod
    def write_csv(self, filename: str, rows: List[Dict[str, Any]]) -> bool:
        """ pass """


class CSVFileWriter(FileWriter):
    def write_csv(self, filename: str, rows: List[Dict[str, Any]]) -> bool:
        try:
            with open(filename, 'w', newline='') as file_handle:
                writer = csv.DictWriter(file_handle, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            return True
        except IOError:
            return False


class OrderHandler(ABC):
    @abstractmethod
    def can_handle(self, order: Order) -> bool:
        """ pass """

    @abstractmethod
    def process(self, order: Order) -> None:
        """ pass """


class TypeAOrderHandler(OrderHandler):
    def __init__(self, file_writer: FileWriter):
        self.file_writer = file_writer

    def can_handle(self, order: Order) -> bool:
        return order.type == 'A'

    def process(self, order: Order) -> None:
        csv_file = f'orders_type_A_{order.id}_{int(time.time())}.csv'
        
        rows = [{
            'ID': order.id,
            'Type': order.type,
            'Amount': order.amount,
            'Flag': str(order.flag).lower(),
            'Status': order.status,
            'Priority': order.priority,
            'Note': 'High value order' if order.amount > 150 else ''
        }]

        if self.file_writer.write_csv(csv_file, rows):
            order.status = 'exported'
        else:
            order.status = 'export_failed'


class TypeBOrderHandler(OrderHandler):
    def __init__(self, api_client: APIClient):
        self.api_client = api_client

    def can_handle(self, order: Order) -> bool:
        return order.type == 'B'

    def process(self, order: Order) -> None:
        try:
            api_response = self.api_client.call_api(order.id)

            if api_response.status == 'success':
                if api_response.data >= 50 and order.amount < 100:
                    order.status = 'processed'
                elif api_response.data < 50 or order.flag:
                    order.status = 'pending'
                else:
                    order.status = 'error'
            else:
                order.status = 'api_error'
        except APIException:
            order.status = 'api_failure'


class TypeCOrderHandler(OrderHandler):
    def can_handle(self, order: Order) -> bool:
        return order.type == 'C'

    def process(self, order: Order) -> None:
        order.status = 'completed' if order.flag else 'in_progress'


class DefaultOrderHandler(OrderHandler):
    def can_handle(self, order: Order) -> bool:
        return True

    def process(self, order: Order) -> None:
        order.status = 'unknown_type'


class PriorityCalculator:
    @staticmethod
    def calculate(order: Order) -> str:
        return 'high' if order.amount > 200 else 'low'


class OrderProcessor:
    def __init__(self, db_service: DatabaseService, handlers: List[OrderHandler]):
        self.db_service = db_service
        self.handlers = handlers

    def process_orders(self, user_id: int) -> bool:
        try:
            orders = self.db_service.get_orders_by_user(user_id)

            if not orders:
                return False

            for order in orders:
                self._process_single_order(order)

            return True
        except Exception:
            return False

    def _process_single_order(self, order: Order) -> None:
        handler = self._get_handler(order)
        handler.process(order)
        
        order.priority = PriorityCalculator.calculate(order)
        
        try:
            self.db_service.update_order_status(order.id, order.status, order.priority)
        except DatabaseException:
            order.status = 'db_error'

    def _get_handler(self, order: Order) -> OrderHandler:
        for handler in self.handlers:
            if handler.can_handle(order):
                return handler
        return DefaultOrderHandler()


class OrderProcessingService:
    def __init__(self, db_service: DatabaseService, api_client: APIClient, file_writer: Optional[FileWriter] = None):
        self.order_processor = OrderProcessor(
            db_service=db_service,
            handlers=[
                TypeAOrderHandler(file_writer or CSVFileWriter()),
                TypeBOrderHandler(api_client),
                TypeCOrderHandler()
            ]
        )

    def process_orders(self, user_id: int) -> bool:
        return self.order_processor.process_orders(user_id)
