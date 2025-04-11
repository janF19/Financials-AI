from unittest.mock import patch, MagicMock
from pathlib import Path
import pytest

from backend.processors.workflow import ValuationWorkflow
from backend.config.settings import settings

@pytest.fixture
def mock_processors(mocker):
    """Mocks all external processors used by the workflow."""
    mock_ocr = mocker.patch('backend.processors.workflow.OCRProcessor', autospec=True)
    mock_extractor = mocker.patch('backend.processors.workflow.FinancialExtractor', autospec=True)
    mock_valuator = mocker.patch('backend.processors.workflow.CompanyValuator', autospec=True)
    mock_generator = mocker.patch('backend.processors.workflow.ReportGenerator', autospec=True)
    mock_save = mocker.patch('backend.processors.workflow.save_report', autospec=True)
    mock_cleanup = mocker.patch('backend.processors.workflow.cleanup_temp_file', autospec=True)

    # Configure return values
    mock_ocr.return_value.process_document.return_value = "<html>Mock HTML</html>"
    mock_extractor.return_value.extract_from_html.return_value = {"revenue": 1000}
    mock_valuator.return_value.calculate_multiples.return_value = {"multiple": 5}
    mock_report_obj = MagicMock()
    mock_generator.generate.return_value = mock_report_obj
    mock_save.return_value = "http://mock.com/report.docx"

    return {
        "ocr": mock_ocr, "extractor": mock_extractor, "valuator": mock_valuator,
        "generator": mock_generator, "save_report": mock_save, "cleanup": mock_cleanup,
        "report_obj": mock_report_obj
    }

def test_workflow_success(mock_processors):
    workflow = ValuationWorkflow()
    test_file = Path(settings.TEMP_STORAGE_PATH) / "test.pdf"
    # Create dummy file for path existence checks if needed
    test_file.parent.mkdir(exist_ok=True)
    test_file.touch()

    result = workflow.execute(str(test_file), user_id="test_user", report_id="test_report")

    assert result["status"] == "success"
    assert result["report_url"] == "http://mock.com/report.docx"

    # Assert processors were called
    mock_processors["ocr"].return_value.process_document.assert_called_once_with(str(test_file), format="html")
    mock_processors["extractor"].return_value.extract_from_html.assert_called_once_with("<html>Mock HTML</html>")
    # ... assert other calls

    # Assert save_report was called
    mock_processors["save_report"].assert_called_once()
    # Assert report object's save method was called
    mock_processors["report_obj"].save.assert_called_once()

    # Assert cleanup happened (check number of calls)
    # Cleanup happens for: temp report, financial data, valuation data, original file
    assert mock_processors["cleanup"].call_count >= 4

    # Clean up dummy file
    test_file.unlink()


def test_workflow_ocr_failure(mock_processors, mocker):
    # Simulate OCR failure
    mock_processors["ocr"].return_value.process_document.side_effect = ValueError("OCR API Failed")
    # Mock logger to check error messages
    mock_logger = mocker.patch('backend.processors.workflow.logger')

    workflow = ValuationWorkflow()
    test_file = Path(settings.TEMP_STORAGE_PATH) / "test_fail.pdf"
    test_file.touch()

    with pytest.raises(ValueError, match="OCR API Failed"):
         workflow.execute(str(test_file), user_id="test_user", report_id="test_report")

    # Assert error was logged
    mock_logger.error.assert_called_with("OCR processing failed: OCR API Failed")
    # Assert subsequent steps were NOT called
    mock_processors["extractor"].return_value.extract_from_html.assert_not_called()
    mock_processors["save_report"].assert_not_called()
    # Assert cleanup was still attempted for any files created before the error
    # Depends on exact implementation, might need more specific mocking/assertions

    test_file.unlink()

# Add more tests for failures in other stages (extraction, valuation, report gen, saving)