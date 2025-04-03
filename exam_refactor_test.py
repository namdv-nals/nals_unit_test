import pytest
from unittest.mock import MagicMock, patch
from exam_refactor import (
    Order, OrderProcessor, OrderProcessingService, DatabaseService, APIClient, FileWriter, CSVFileWriter,
    TypeAOrderHandler, TypeBOrderHandler, TypeCOrderHandler, DefaultOrderHandler, APIResponse, 
    DatabaseException, APIException, PriorityCalculator
)
import tempfile
import os
import csv

@pytest.fixture
def mock_db_service():
    return MagicMock(spec=DatabaseService)

@pytest.fixture
def mock_api_client():
    return MagicMock(spec=APIClient)

@pytest.fixture
def mock_file_writer():
    return MagicMock(spec=FileWriter)

@pytest.fixture
def order_processor(mock_db_service, mock_api_client, mock_file_writer):
    return OrderProcessor(
        db_service=mock_db_service,
        handlers=[
            TypeAOrderHandler(mock_file_writer),
            TypeBOrderHandler(mock_api_client),
            TypeCOrderHandler(),
            DefaultOrderHandler()
        ]
    )

def test_no_orders(order_processor, mock_db_service):
    mock_db_service.get_orders_by_user.return_value = []
    assert order_processor.process_orders(1) == False

def test_database_exception(order_processor, mock_db_service):
    mock_db_service.get_orders_by_user.side_effect = DatabaseException
    assert order_processor.process_orders(1) == False

def test_type_a_order_success(order_processor, mock_db_service, mock_file_writer):
    order = Order(id=1, type='A', amount=100, flag=False)
    mock_db_service.get_orders_by_user.return_value = [order]
    mock_file_writer.write_csv.return_value = True
    
    assert order_processor.process_orders(1) == True
    assert order.status == 'exported'

def test_type_a_order_file_fail(order_processor, mock_db_service, mock_file_writer):
    order = Order(id=1, type='A', amount=100, flag=False)
    mock_db_service.get_orders_by_user.return_value = [order]
    mock_file_writer.write_csv.return_value = False
    
    assert order_processor.process_orders(1) == True
    assert order.status == 'export_failed'

def test_type_b_order_api_success_processed(order_processor, mock_db_service, mock_api_client):
    order = Order(id=1, type='B', amount=80, flag=False)
    mock_db_service.get_orders_by_user.return_value = [order]
    mock_api_client.call_api.return_value = APIResponse(status='success', data=60)
    
    assert order_processor.process_orders(1) == True
    assert order.status == 'processed'

def test_type_b_order_api_success_pending_data_lt_50(order_processor, mock_db_service, mock_api_client):
    order = Order(id=1, type='B', amount=80, flag=False)
    mock_db_service.get_orders_by_user.return_value = [order]
    mock_api_client.call_api.return_value = APIResponse(status='success', data=40)
    
    assert order_processor.process_orders(1) == True
    assert order.status == 'pending'

def test_type_b_order_api_success_pending_flag_true(order_processor, mock_db_service, mock_api_client):
    order = Order(id=1, type='B', amount=80, flag=True)
    mock_db_service.get_orders_by_user.return_value = [order]
    mock_api_client.call_api.return_value = APIResponse(status='success', data=60)
    
    assert order_processor.process_orders(1) == True
    assert order.status == 'processed'

def test_type_b_order_api_success_error(order_processor, mock_db_service, mock_api_client):
    order = Order(id=1, type='B', amount=100, flag=False)
    mock_db_service.get_orders_by_user.return_value = [order]
    mock_api_client.call_api.return_value = APIResponse(status='success', data=60)
    
    assert order_processor.process_orders(1) == True
    assert order.status == 'error'

def test_type_b_order_api_failure(order_processor, mock_db_service, mock_api_client):
    order = Order(id=1, type='B', amount=80, flag=False)
    mock_db_service.get_orders_by_user.return_value = [order]
    mock_api_client.call_api.return_value = APIResponse(status='error', data=0)
    
    assert order_processor.process_orders(1) == True
    assert order.status == 'api_error'

def test_type_b_order_api_exception(order_processor, mock_db_service, mock_api_client):
    order = Order(id=1, type='B', amount=80, flag=False)
    mock_db_service.get_orders_by_user.return_value = [order]
    mock_api_client.call_api.side_effect = APIException
    
    assert order_processor.process_orders(1) == True
    assert order.status == 'api_failure'

def test_priority_high(order_processor, mock_db_service):
    order = Order(id=1, type='C', amount=300, flag=True)
    mock_db_service.get_orders_by_user.return_value = [order]
    mock_db_service.update_order_status.return_value = True
    
    assert order_processor.process_orders(1) == True
    assert order.priority == 'high'

def test_db_update_fail(order_processor, mock_db_service):
    order = Order(id=1, type='C', amount=50, flag=False)
    mock_db_service.get_orders_by_user.return_value = [order]
    mock_db_service.update_order_status.side_effect = DatabaseException
    
    assert order_processor.process_orders(1) == True
    assert order.status == 'db_error'

def test_database_service_get_orders(mock_db_service):
    order = Order(id=1, type='A', amount=100, flag=False)
    mock_db_service.get_orders_by_user.return_value = [order]
    
    orders = mock_db_service.get_orders_by_user(1)
    assert len(orders) == 1
    assert orders[0].type == 'A'

def test_database_service_update_status(mock_db_service):
    mock_db_service.update_order_status.return_value = True
    assert mock_db_service.update_order_status(1, "processed", "low") == True

def test_api_client_call(mock_api_client):
    mock_api_client.call_api.return_value = APIResponse(status="success", data=100)
    
    response = mock_api_client.call_api(1)
    assert response.status == "success"
    assert response.data == 100

def test_file_writer(mock_file_writer):
    mock_file_writer.write_csv.return_value = True
    assert mock_file_writer.write_csv("test.csv", [{"id": 1}]) == True

def test_csv_file_writer():
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file_path = temp_file.name 
        temp_file.close()
    
    writer = CSVFileWriter()
    success = writer.write_csv(temp_file_path, [
        {"id": 1, "name": "Test"}
    ])
    
    assert success == True 
    
    with open(temp_file_path, "r") as f:
        content = f.read()
        assert "id,name" in content 
        assert "1,Test" in content
    
    os.remove(temp_file_path)

def test_csv_file_writer_failure():
    with patch('builtins.open', side_effect=IOError("Failed to open file")):
        writer = CSVFileWriter()
        success = writer.write_csv("/invalid/path/test.csv", [{"id": 1}])
        assert success == False

def test_default_order_handler():
    order = Order(id=1, type='X', amount=50, flag=False)
    handler = DefaultOrderHandler()

    assert handler.can_handle(order) == True
    
    handler.process(order)
    assert order.status == "unknown_type"

def test_order_processing_service():
    mock_db_service = MagicMock(spec=DatabaseService)
    mock_api_client = MagicMock(spec=APIClient)
    
    service = OrderProcessingService(mock_db_service, mock_api_client)
    mock_db_service.get_orders_by_user.return_value = [Order(id=1, type='A', amount=100, flag=False)]
    
    result = service.process_orders(1)
    assert result == True

def test_order_processor_get_handler_default():
    mock_db_service = MagicMock(spec=DatabaseService)
    order = Order(id=1, type='D', amount=50, flag=False)
    mock_db_service.get_orders_by_user.return_value = [order]
    
    processor = OrderProcessor(
        db_service=mock_db_service,
        handlers=[TypeAOrderHandler(MagicMock())]  # Only has handler for type A
    )
    
    assert processor.process_orders(1) == True
    assert order.status == "unknown_type"

def test_priority_calculator():
    high_order = Order(id=1, type='A', amount=250, flag=False)
    low_order = Order(id=2, type='B', amount=150, flag=False)
    
    assert PriorityCalculator.calculate(high_order) == 'high'
    assert PriorityCalculator.calculate(low_order) == 'low'
