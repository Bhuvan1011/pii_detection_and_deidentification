import argparse
import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple
import logging
from datetime import datetime
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend to avoid threading issues
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF  # For PDF export
import PyPDF2  # For PDF processing

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------
# Enhanced Utility Functions
# ---------------------------

def verhoeff_validate(num: str) -> bool:
    """Validate using Verhoeff checksum (for Aadhaar)."""
    _d = [
        [0,1,2,3,4,5,6,7,8,9], [1,2,3,4,0,6,7,8,9,5], [2,3,4,0,1,7,8,9,5,6],
        [3,4,0,1,2,8,9,5,6,7], [4,0,1,2,3,9,5,6,7,8], [5,9,8,7,6,0,4,3,2,1],
        [6,5,9,8,7,1,0,4,3,2], [7,6,5,9,8,2,1,0,4,3], [8,7,6,5,9,3,2,1,0,4],
        [9,8,7,6,5,4,3,2,1,0]
    ]
    _p = [
        [0,1,2,3,4,5,6,7,8,9], [1,5,7,6,2,8,3,0,9,4], [5,8,0,3,7,9,6,1,4,2],
        [8,9,1,6,0,4,3,5,2,7], [9,4,5,3,1,2,6,8,7,0], [4,2,8,6,5,7,3,9,0,1],
        [2,7,9,3,8,0,6,4,1,5], [7,0,4,6,9,1,3,2,5,8]
    ]
    try:
        c = 0
        for i, item in enumerate(reversed(num)):
            c = _d[c][_p[(i % 8)][int(item)]]
        return c == 0
    except Exception:
        return False

def luhn_check(number: str) -> bool:
    """Return True if number passes Luhn mod-10."""
    digits = [int(ch) for ch in re.sub(r"\D", "", number)]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    dbl = False
    for d in reversed(digits):
        if dbl:
            d = d * 2
            if d > 9:
                d -= 9
        checksum += d
        dbl = not dbl
    return checksum % 10 == 0

def validate_indian_phone(phone: str) -> bool:
    """Validate Indian mobile numbers (10 digits starting with 6-9)."""
    digits = re.sub(r"\D", "", phone)
    return len(digits) == 10 and digits[0] in '6789'

def validate_ifsc(ifsc: str) -> bool:
    """Validate IFSC code format (4 letters + 0 + 6 alphanumeric)."""
    return bool(re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', ifsc.upper()))

def validate_voter_id(voter_id: str) -> bool:
    """Validate Indian Voter ID (3 letters + 7 digits)."""
    return bool(re.match(r'^[A-Z]{3}\d{7}$', voter_id.upper()))

def validate_driving_license(dl: str) -> bool:
    """Validate Indian Driving License (state code + digits)."""
    return bool(re.match(r'^[A-Z]{2}\d{2}/\d{6}/\d{4}$', dl.upper()))

def validate_ip(ip: str) -> bool:
    """Validate IP address."""
    parts = ip.split('.')
    return len(parts) == 4 and all(0 <= int(p) <= 255 for p in parts if p.isdigit())

def validate_dob(dob: str) -> bool:
    """Validate date of birth (dd/mm/yyyy)."""
    try:
        datetime.strptime(dob, '%d/%m/%Y')
        return True
    except ValueError:
        return False

def validate_medical_id(mid: str) -> bool:
    """Validate Medical ID (MED + 8 alphanumeric)."""
    return bool(re.match(r'^MED[A-Z0-9]{8}$', mid.upper()))

# ---------------------------
# Enhanced Patterns
# ---------------------------
ENHANCED_PII_PATTERNS = {
    "aadhaar": re.compile(r"\b(?:(\d{4}\s\d{4}\s\d{4})|(\d{12}))\b"),
    "pan": re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"\b(?:\+91[-\s]?)?(?:[6-9]\d{9}|[6-9]\d{2}[-\s]\d{3}[-\s]\d{4})\b"),
    "ifsc": re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b"),
    "bank_account": re.compile(r"\b\d{9,18}\b"),
    "voter_id": re.compile(r"\b([A-Z]{3}\d{7})\b"),
    "driving_license": re.compile(r"\b([A-Z]{2}\d{2}/\d{6}/\d{4})\b"),
    "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "dob": re.compile(r"\b(\d{2}/\d{2}/\d{4})\b"),
    "medical_id": re.compile(r"\b(MED[A-Z0-9]{8})\b"),
}

# ---------------------------
# Enhanced De-identification
# ---------------------------
def mask_credit_card_enhanced(cc: str) -> str:
    """Enhanced credit card masking with better formatting preservation."""
    digits = re.sub(r"\D", "", cc)
    if len(digits) < 13:
        return cc
    
    masked_digits = 'X' * (len(digits) - 4) + digits[-4:]
    
    result = []
    digit_idx = 0
    for char in cc:
        if char.isdigit():
            result.append(masked_digits[digit_idx])
            digit_idx += 1
        else:
            result.append(char)
    return ''.join(result)

def mask_phone_enhanced(phone: str) -> str:
    """Mask phone number showing only last 4 digits."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 10:
        return phone
    
    masked = 'X' * (len(digits) - 4) + digits[-4:]
    
    result = []
    digit_idx = 0
    for char in phone:
        if char.isdigit():
            result.append(masked[digit_idx])
            digit_idx += 1
        else:
            result.append(char)
    return ''.join(result)

def anonymize_bank_account(account: str) -> str:
    """Anonymize bank account with hash-based token."""
    token = hashlib.sha256(account.encode("utf-8")).hexdigest()[:12].upper()
    return f"ACCT_{token}"

def anonymize_ifsc(ifsc: str) -> str:
    """Anonymize IFSC but keep bank code pattern."""
    bank_code = ifsc[:4]
    token = hashlib.md5(ifsc.encode()).hexdigest()[:6].upper()
    return f"{bank_code}0{token}"

def mask_aadhaar(a: str) -> str:
    """Mask middle 4 digits; keep formatting if spaces exist."""
    digits = re.sub(r"\D", "", a)
    if len(digits) != 12:
        return a
    masked = digits[:4] + "XXXX" + digits[-4:]
    if " " in a:
        return f"{masked[:4]} {masked[4:8]} {masked[8:]}"
    return masked

def anonymize_pan(pan: str) -> str:
    """Irreversibly anonymize PAN to a stable token."""
    token = hashlib.sha256(pan.encode("utf-8")).hexdigest()[:10].upper()
    return f"PAN_{token}"

def pseudo_email(email: str) -> str:
    """Keep domain; mask local part."""
    try:
        local, domain = email.split("@", 1)
        return "xxxx@" + domain
    except ValueError:
        return "xxxx@"

def mask_voter_id(vid: str) -> str:
    """Mask Voter ID."""
    return vid[:3] + 'X' * 4 + vid[-3:]

def mask_driving_license(dl: str) -> str:
    """Mask Driving License."""
    parts = dl.split('/')
    if len(parts) == 3:
        return parts[0] + '/XXXXXX/' + parts[2]
    return dl

def mask_ip(ip: str) -> str:
    """Mask IP address."""
    parts = ip.split('.')
    return '.'.join(parts[:2] + ['X', 'X'])

def mask_dob(dob: str) -> str:
    """Mask DOB to year only."""
    return 'XX/XX/' + dob.split('/')[-1]

def anonymize_medical_id(mid: str) -> str:
    """Anonymize Medical ID."""
    token = hashlib.sha256(mid.encode("utf-8")).hexdigest()[:8].upper()
    return f"MED{token}"

ENHANCED_DEIDENTIFY = {
    "credit_card": mask_credit_card_enhanced,
    "aadhaar": mask_aadhaar,
    "pan": anonymize_pan,
    "email": pseudo_email,
    "phone": mask_phone_enhanced,
    "ifsc": anonymize_ifsc,
    "bank_account": anonymize_bank_account,
    "voter_id": mask_voter_id,
    "driving_license": mask_driving_license,
    "ip_address": mask_ip,
    "dob": mask_dob,
    "medical_id": anonymize_medical_id,
}

# ---------------------------
# Enhanced Data Classes
# ---------------------------
@dataclass
class EnhancedDetection:
    row_index: int
    column_name: str
    pii_type: str
    raw_value: str
    masked_value: str
    start: int
    end: int
    confidence: float = 1.0
    context: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'row_index': self.row_index,
            'column_name': self.column_name,
            'pii_type': self.pii_type,
            'raw_value': self.raw_value,
            'masked_value': self.masked_value,
            'start': self.start,
            'end': self.end,
            'confidence': self.confidence,
            'context': self.context
        }

# ---------------------------
# Enhanced Detector
# ---------------------------
class EnhancedPiiDetector:
    def __init__(self, confidence_threshold: float = 0.7):
        self.patterns = ENHANCED_PII_PATTERNS
        self.confidence_threshold = confidence_threshold

    def _calculate_confidence(self, pii_type: str, match_text: str, context: str = "") -> float:
        base_confidence = 1.0
        
        if pii_type == "credit_card":
            if luhn_check(match_text):
                return 0.95
            else:
                return 0.3
        
        if pii_type == "aadhaar":
            digits = re.sub(r"\D", "", match_text)
            if len(digits) == 12 and verhoeff_validate(digits):
                return 0.95
            elif len(digits) == 12:
                return 0.7
            else:
                return 0.3
        
        if pii_type == "phone":
            if validate_indian_phone(match_text):
                return 0.9
            else:
                return 0.4
        
        if pii_type == "ifsc":
            if validate_ifsc(match_text):
                return 0.95
            else:
                return 0.5
        
        if pii_type == "bank_account":
            digits = re.sub(r"\D", "", match_text)
            if 9 <= len(digits) <= 18:
                context_lower = context.lower()
                if any(keyword in context_lower for keyword in ['account', 'bank', 'acc', 'a/c']):
                    return 0.8
                return 0.6
            return 0.3
        
        if pii_type == "voter_id":
            if validate_voter_id(match_text):
                return 0.9
            return 0.4
        
        if pii_type == "driving_license":
            if validate_driving_license(match_text):
                return 0.9
            return 0.4
        
        if pii_type == "ip_address":
            if validate_ip(match_text):
                return 0.95
            return 0.5
        
        if pii_type == "dob":
            if validate_dob(match_text):
                return 0.8
            return 0.3
        
        if pii_type == "medical_id":
            if validate_medical_id(match_text):
                return 0.7
            return 0.3
        
        return base_confidence

    def find_all_enhanced(self, text: str, context: str = "") -> List[Tuple[str, re.Match, float]]:
        results = []
        for pii_type, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                candidate = match.group(0)
                confidence = self._calculate_confidence(pii_type, candidate, context)
                
                if confidence >= self.confidence_threshold:
                    results.append((pii_type, match, confidence))
        
        return results

# ---------------------------
# Enhanced Processor
# ---------------------------
class EnhancedProcessor:
    def __init__(self, encoding: str = "utf-8", confidence_threshold: float = 0.7):
        self.detector = EnhancedPiiDetector(confidence_threshold)
        self.encoding = encoding
        self.det_counts = Counter()
        self.confidence_stats = defaultdict(list)

    def _deidentify_text_enhanced(self, text: str, context: str = "") -> Tuple[str, List[EnhancedDetection]]:
        detections: List[EnhancedDetection] = []
        all_matches = self.detector.find_all_enhanced(text, context)
        
        if not all_matches:
            return text, detections

        new_text = text
        all_matches.sort(key=lambda x: x[1].start(), reverse=True)
        
        for pii_type, match, confidence in all_matches:
            raw = match.group(0)
            masked = ENHANCED_DEIDENTIFY[pii_type](raw)
            new_text = new_text[:match.start()] + masked + new_text[match.end():]
            
            detection = EnhancedDetection(
                row_index=-1,
                column_name="",
                pii_type=pii_type,
                raw_value=raw,
                masked_value=masked,
                start=match.start(),
                end=match.end(),
                confidence=confidence,
                context=context[:100] if context else ""
            )
            detections.append(detection)
            self.det_counts[pii_type] += 1
            self.confidence_stats[pii_type].append(confidence)

        return new_text, list(reversed(detections))

    def _clean_csv(self, input_path: str) -> str:
        """Clean CSV file by removing Markdown delimiters and empty lines."""
        with open(input_path, 'r', encoding=self.encoding) as f:
            lines = f.readlines()
        
        # Remove Markdown code block delimiters and empty lines
        cleaned_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('```')]
        
        # Log raw content for debugging
        logger.info(f"Raw CSV content: {cleaned_lines}")
        
        # Write cleaned content to a temporary file
        cleaned_path = input_path + '.cleaned'
        with open(cleaned_path, 'w', encoding=self.encoding, newline='') as f:
            f.write('\n'.join(cleaned_lines))
        
        return cleaned_path
    


    def process_csv_enhanced(self, input_path: str, output_path: str, report_dir: str) -> Dict:
        # Clean the CSV file before processing
        cleaned_input_path = self._clean_csv(input_path)
        try:
            result = self._process_tabular(cleaned_input_path, output_path, report_dir, 
                                        reader_func=lambda x: pd.read_csv(x, index_col=None), 
                                        writer_func=pd.DataFrame.to_csv)
        finally:
            # Clean up temporary file
            if os.path.exists(cleaned_input_path):
                os.remove(cleaned_input_path)
        return result

    def process_excel_enhanced(self, input_path: str, output_path: str, report_dir: str) -> Dict:
        return self._process_tabular(input_path, output_path, report_dir, 
                                    reader_func=lambda x: pd.read_excel(x, index_col=None), 
                                    writer_func=pd.DataFrame.to_excel)

    def _process_tabular(self, input_path: str, output_path: str, report_dir: str, reader_func, writer_func) -> Dict:
        os.makedirs(report_dir, exist_ok=True)
        
        detections_log_path = os.path.join(report_dir, "detections.csv")
        summary_json_path = os.path.join(report_dir, "summary.json")
        summary_txt_path = os.path.join(report_dir, "summary.txt")
        
        detections_log: List[EnhancedDetection] = []
        
        logger.info(f"Processing tabular file: {input_path}")
        
        try:
            df = reader_func(input_path)
            logger.info(f"DataFrame index: {df.index}")
            logger.info(f"DataFrame columns: {list(df.columns)}")
            # Ensure index is reset to integers if needed
            if not isinstance(df.index, pd.RangeIndex):
                df = df.reset_index(drop=True)
                logger.info(f"Reset index to RangeIndex: {df.index}")
            header = list(df.columns)
            new_df = df.copy()
            
            for r_i, row in df.iterrows():
                row_context = " ".join(str(val) for val in row if pd.notna(val))
                # Handle index as integer
                row_index = int(r_i)
                for c_i, col in enumerate(header):
                    cell = str(row[col]) if pd.notna(row[col]) else ""
                    new_text, dets = self._deidentify_text_enhanced(cell, row_context)
                    for detection in dets:
                        detection.row_index = row_index + 1  # 1-indexed
                        detection.column_name = col
                        detections_log.append(detection)
                    new_df.at[r_i, col] = new_text
            
            writer_func(new_df, output_path, index=False)
            
            with open(detections_log_path, "w", encoding=self.encoding, newline="") as detf:
                det_writer = csv.writer(detf)
                det_writer.writerow([
                    "row_index", "column_name", "pii_type", "raw_value", 
                    "masked_value", "start", "end", "confidence", "context"
                ])
                for det in detections_log:
                    det_writer.writerow([
                        det.row_index, det.column_name, det.pii_type,
                        det.raw_value, det.masked_value, det.start,
                        det.end, f"{det.confidence:.3f}", det.context
                    ])

            summary = self._generate_summary(input_path, output_path, detections_log)
            
            with open(summary_json_path, "w", encoding=self.encoding) as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            with open(summary_txt_path, "w", encoding=self.encoding) as f:
                f.write(json.dumps(summary, indent=2, ensure_ascii=False))
            
            logger.info(f"Processing complete. Found {len(detections_log)} PII instances.")
            return {"summary": summary, "detections": [d.to_dict() for d in detections_log]}
        
        except Exception as e:
            logger.error(f"Error processing tabular file: {str(e)}")
            raise

    def process_json_enhanced(self, input_path: str, output_path: str, report_dir: str) -> Dict:
        os.makedirs(report_dir, exist_ok=True)
        
        detections_log_path = os.path.join(report_dir, "detections.csv")
        summary_json_path = os.path.join(report_dir, "summary.json")
        summary_txt_path = os.path.join(report_dir, "summary.txt")
        
        detections_log: List[EnhancedDetection] = []
        
        logger.info(f"Processing JSON: {input_path}")
        
        try:
            with open(input_path, "r", encoding=self.encoding) as f:
                data = json.load(f)
            
            if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
                raise ValueError("JSON must be a list of dictionaries")
            
            new_data = []
            for r_i, item in enumerate(data, start=1):
                item_context = " ".join(f"{k}:{v}" for k, v in item.items())
                new_item = {}
                for key, value in item.items():
                    cell = str(value) if value is not None else ""
                    new_text, dets = self._deidentify_text_enhanced(cell, item_context)
                    for detection in dets:
                        detection.row_index = r_i
                        detection.column_name = key
                        detections_log.append(detection)
                    new_item[key] = new_text
                new_data.append(new_item)
            
            with open(output_path, "w", encoding=self.encoding) as f:
                json.dump(new_data, f, indent=2, ensure_ascii=False)
            
            with open(detections_log_path, "w", encoding=self.encoding, newline="") as detf:
                det_writer = csv.writer(detf)
                det_writer.writerow([
                    "row_index", "column_name", "pii_type", "raw_value", 
                    "masked_value", "start", "end", "confidence", "context"
                ])
                for det in detections_log:
                    det_writer.writerow([
                        det.row_index, det.column_name, det.pii_type,
                        det.raw_value, det.masked_value, det.start,
                        det.end, f"{det.confidence:.3f}", det.context
                    ])

            summary = self._generate_summary(input_path, output_path, detections_log)
            
            with open(summary_json_path, "w", encoding=self.encoding) as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            with open(summary_txt_path, "w", encoding=self.encoding) as f:
                f.write(json.dumps(summary, indent=2, ensure_ascii=False))
            
            logger.info(f"Processing complete. Found {len(detections_log)} PII instances.")
            return {"summary": summary, "detections": [d.to_dict() for d in detections_log]}
        
        except Exception as e:
            logger.error(f"Error processing JSON: {str(e)}")
            raise

    def process_txt_enhanced(self, input_path: str, output_path: str, report_dir: str) -> Dict:
        os.makedirs(report_dir, exist_ok=True)
        
        detections_log_path = os.path.join(report_dir, "detections.csv")
        summary_json_path = os.path.join(report_dir, "summary.json")
        summary_txt_path = os.path.join(report_dir, "summary.txt")
        
        detections_log: List[EnhancedDetection] = []
        
        logger.info(f"Processing TXT: {input_path}")
        
        try:
            with open(input_path, "r", encoding=self.encoding) as f:
                text = f.read()
            
            new_text, dets = self._deidentify_text_enhanced(text, text)
            for detection in dets:
                detection.row_index = 1  # Treat as single row
                detection.column_name = "text"
                detections_log.append(detection)
            
            with open(output_path, "w", encoding=self.encoding) as f:
                f.write(new_text)
            
            with open(detections_log_path, "w", encoding=self.encoding, newline="") as detf:
                det_writer = csv.writer(detf)
                det_writer.writerow([
                    "row_index", "column_name", "pii_type", "raw_value", 
                    "masked_value", "start", "end", "confidence", "context"
                ])
                for det in detections_log:
                    det_writer.writerow([
                        det.row_index, det.column_name, det.pii_type,
                        det.raw_value, det.masked_value, det.start,
                        det.end, f"{det.confidence:.3f}", det.context
                    ])

            summary = self._generate_summary(input_path, output_path, detections_log)
            
            with open(summary_json_path, "w", encoding=self.encoding) as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            with open(summary_txt_path, "w", encoding=self.encoding) as f:
                f.write(json.dumps(summary, indent=2, ensure_ascii=False))
            
            logger.info(f"Processing complete. Found {len(detections_log)} PII instances.")
            return {"summary": summary, "detections": [d.to_dict() for d in detections_log]}
        
        except Exception as e:
            logger.error(f"Error processing TXT: {str(e)}")
            raise

    def process_pdf_enhanced(self, input_path: str, output_path: str, report_dir: str) -> Dict:
        os.makedirs(report_dir, exist_ok=True)
        
        detections_log_path = os.path.join(report_dir, "detections.csv")
        summary_json_path = os.path.join(report_dir, "summary.json")
        summary_txt_path = os.path.join(report_dir, "summary.txt")
        
        detections_log: List[EnhancedDetection] = []
        
        logger.info(f"Processing PDF: {input_path}")
        
        try:
            with open(input_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            
            new_text, dets = self._deidentify_text_enhanced(text, text)
            for detection in dets:
                detection.row_index = 1  # Treat as single row
                detection.column_name = "pdf_text"
                detections_log.append(detection)
            
            with open(output_path, "w", encoding=self.encoding) as f:
                f.write(new_text)
            
            with open(detections_log_path, "w", encoding=self.encoding, newline="") as detf:
                det_writer = csv.writer(detf)
                det_writer.writerow([
                    "row_index", "column_name", "pii_type", "raw_value", 
                    "masked_value", "start", "end", "confidence", "context"
                ])
                for det in detections_log:
                    det_writer.writerow([
                        det.row_index, det.column_name, det.pii_type,
                        det.raw_value, det.masked_value, det.start,
                        det.end, f"{det.confidence:.3f}", det.context
                    ])

            summary = self._generate_summary(input_path, output_path, detections_log)
            
            with open(summary_json_path, "w", encoding=self.encoding) as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            with open(summary_txt_path, "w", encoding=self.encoding) as f:
                f.write(json.dumps(summary, indent=2, ensure_ascii=False))
            
            logger.info(f"Processing complete. Found {len(detections_log)} PII instances.")
            return {"summary": summary, "detections": [d.to_dict() for d in detections_log]}
        
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise
    
    def process_file(self, input_path: str, output_path: str, report_dir: str, confidence_threshold: float = 0.7) -> Dict:
        file_ext = os.path.splitext(input_path)[1].lower()
        if file_ext == ".csv":
            return self.process_csv_enhanced(input_path, output_path, report_dir)
        elif file_ext in [".xls", ".xlsx"]:
            return self.process_excel_enhanced(input_path, output_path, report_dir)
        elif file_ext == ".json":
            return self.process_json_enhanced(input_path, output_path, report_dir)
        elif file_ext == ".txt":
            return self.process_txt_enhanced(input_path, output_path, report_dir)
        elif file_ext == ".pdf":
            return self.process_pdf_enhanced(input_path, output_path, report_dir)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")


    def _generate_summary(self, input_path: str, output_path: str, detections: List[EnhancedDetection]) -> Dict:
        summary = {
            "timestamp": datetime.now().isoformat(),
            "input_file": os.path.abspath(input_path),
            "output_file": os.path.abspath(output_path),
            "total_detections": len(detections),
            "counts_by_type": dict(self.det_counts),
            "unique_values_by_type": {
                pii_type: len(set(d.raw_value for d in detections if d.pii_type == pii_type))
                for pii_type in self.det_counts.keys()
            },
            "average_confidence_by_type": {
                pii_type: sum(self.confidence_stats[pii_type]) / len(self.confidence_stats[pii_type]) if self.confidence_stats[pii_type] else 0
                for pii_type in self.det_counts.keys()
            },
            "estimated_precision": {
                pii_type: max(0.5, sum(c > 0.8 for c in self.confidence_stats[pii_type]) / len(self.confidence_stats[pii_type]) if self.confidence_stats[pii_type] else 0)
                for pii_type in self.det_counts.keys()
            },
        }
        return summary

    def generate_visual_report(self, report_dir: str, output_path: str):
        

        detections_path = os.path.join(report_dir, "detections.csv")
        if not os.path.exists(detections_path):
            logger.warning(f"Detections file not found: {detections_path}")
            return

        df = pd.read_csv(detections_path)
        
        # Summary metrics
        total_detections = len(df)
        pii_types = df['pii_type'].nunique()
        unique_values = df['raw_value'].nunique()
        avg_confidence = df['confidence'].mean()
        
        summary_table = pd.DataFrame({
            "Metric": ["Total Detections", "Unique PII Values", "PII Types Detected", "Average Confidence"],
            "Value": [total_detections, unique_values, pii_types, round(avg_confidence,3)]
        })
        
        os.makedirs(report_dir, exist_ok=True)
        image_paths = []

        # 1️⃣ Bar Chart
        plt.figure(figsize=(10,6))
        sns.countplot(data=df, x='pii_type', palette='Set2', order=df['pii_type'].value_counts().index)
        plt.title('PII Detections by Type', fontsize=14)
        plt.ylabel('Count')
        plt.xlabel('PII Type')
        plt.xticks(rotation=45)
        bar_chart = os.path.join(report_dir, "bar_chart.png")
        plt.tight_layout()
        plt.savefig(bar_chart)
        plt.close()
        image_paths.append(bar_chart)

        # 2️⃣ Pie Chart
        plt.figure(figsize=(8,8))
        df['pii_type'].value_counts().plot.pie(autopct='%1.1f%%', startangle=140, colors=sns.color_palette('Set2'))
        plt.ylabel('')
        plt.title('Proportion of PII Types', fontsize=14)
        pie_chart = os.path.join(report_dir, "pie_chart.png")
        plt.tight_layout()
        plt.savefig(pie_chart)
        plt.close()
        image_paths.append(pie_chart)

        # 3️⃣ Histogram
        plt.figure(figsize=(10,6))
        sns.histplot(df['confidence'], bins=20, kde=True, color='skyblue')
        plt.title('Confidence Score Distribution', fontsize=14)
        plt.xlabel('Confidence')
        plt.ylabel('Frequency')
        hist_chart = os.path.join(report_dir, "hist_chart.png")
        plt.tight_layout()
        plt.savefig(hist_chart)
        plt.close()
        image_paths.append(hist_chart)

        # 4️⃣ Stacked bar – confidence bins
        df['confidence_bin'] = pd.cut(df['confidence'], bins=[0,0.5,0.7,0.85,1.0], labels=['Low','Medium','High','Very High'])
        stacked_counts = df.pivot_table(index='pii_type', columns='confidence_bin', aggfunc='size', fill_value=0)
        stacked_counts = stacked_counts[['Low','Medium','High','Very High']]
        stacked_counts.plot(kind='bar', stacked=True, figsize=(10,6), colormap='Set2')
        plt.title('PII Counts by Confidence Levels')
        plt.xlabel('PII Type')
        plt.ylabel('Count')
        plt.xticks(rotation=45)
        stacked_chart = os.path.join(report_dir, "stacked_chart.png")
        plt.tight_layout()
        plt.savefig(stacked_chart)
        plt.close()
        image_paths.append(stacked_chart)

        # 5️⃣ Summary table as image
        plt.figure(figsize=(10, summary_table.shape[0]*0.6 + 1))
        plt.axis('off')
        table_plot = plt.table(cellText=summary_table.values, colLabels=summary_table.columns, cellLoc='center', loc='center')
        table_plot.auto_set_font_size(False)
        table_plot.set_fontsize(10)
        plt.title('Summary Table of PII Detections', pad=20)
        summary_table_path = os.path.join(report_dir, "summary_table.png")
        plt.savefig(summary_table_path, bbox_inches='tight')
        plt.close()
        image_paths.append(summary_table_path)

        # Generate PDF
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Page 1 – Overview
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Detection Overview", ln=1, align='C')
        pdf.ln(5)
        pdf.set_font("Arial", '', 12)
        pdf.multi_cell(0, 8, f"Summary of PII detections and processing results.\n\n"
                                f"Total Detections: {total_detections}\n"
                                f"Unique PII Values: {unique_values}\n"
                                f"PII Types Detected: {pii_types}\n"
                                f"Average Confidence: {round(avg_confidence,3)}")
        pdf.ln(5)
        pdf.image(bar_chart, x=15, w=180)
        pdf.add_page()
        pdf.image(pie_chart, x=30, w=150)

        # Page 2 – Confidence & Details
        pdf.add_page()
        pdf.cell(0, 10, "Confidence Distribution", ln=1, align='C')
        pdf.image(hist_chart, x=15, w=180)
        pdf.ln(5)
        pdf.cell(0, 10, "Stacked Confidence Levels by PII Type", ln=1, align='C')
        pdf.image(stacked_chart, x=15, w=180)
        pdf.add_page()
        pdf.cell(0, 10, "Summary Table", ln=1, align='C')
        pdf.image(summary_table_path, x=15, w=180)

        pdf.output(output_path)

        # Clean up temp images
        for img in image_paths:
            if os.path.exists(img):
                os.remove(img)


# ---------------------------
# Enhanced CLI
# ---------------------------
def parse_enhanced_args():
    parser = argparse.ArgumentParser(
        description="Enhanced PII Detection & De-Identification for Indian datasets",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--input", "-i", required=True, help="Input file")
    parser.add_argument("--output", "-o", required=True, help="Output de-identified file")
    parser.add_argument("--report-dir", "-r", required=True, help="Report output directory")
    parser.add_argument("--confidence-threshold", "-c", type=float, default=0.7, 
                        help="Minimum confidence threshold for PII detection")
    parser.add_argument("--encoding", default="utf-8", help="File encoding")
    
    return parser.parse_args()

def main_enhanced():
    args = parse_enhanced_args()
    
    processor = EnhancedProcessor(
        encoding=args.encoding, 
        confidence_threshold=args.confidence_threshold
    )
    
    file_ext = os.path.splitext(args.input)[1].lower()
    if file_ext == '.csv':
        processor.process_csv_enhanced(args.input, args.output, args.report_dir)
    elif file_ext in ['.xls', '.xlsx']:
        processor.process_excel_enhanced(args.input, args.output, args.report_dir)
    elif file_ext == '.json':
        processor.process_json_enhanced(args.input, args.output, args.report_dir)
    elif file_ext == '.txt':
        processor.process_txt_enhanced(args.input, args.output, args.report_dir)
    elif file_ext == '.pdf':
        processor.process_pdf_enhanced(args.input, args.output, args.report_dir)
    else:
        raise ValueError("Unsupported file format")
    
    visual_report_path = os.path.join(args.report_dir, "visual_report.pdf")
    processor.generate_visual_report(args.report_dir, visual_report_path)

if __name__ == "__main__":
    main_enhanced()
