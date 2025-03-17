# Oakland Port Container Management Tools

This repository contains two main tools for managing container operations at the Oakland port and associated warehouses:

## 1. Container Status Checker

A Python-based automation tool that checks container statuses across three terminals at the Port of Oakland:

- Trapac Terminal
- Oakland International Container Terminal (OICT)
- Shippers Transport Express (STE)

### Features

- Multi-terminal status checking in a single run
- Supports batch container number queries
- Retrieves comprehensive container information:
  - Availability status
  - Line operator details
  - Container dimensions
  - Hold statuses (Customs, Line, CBPA, Terminal)
  - Current location
  - Terminal-specific information

### Usage

```bash
python container_status_checker.py CONTAINER_NUMBER [CONTAINER_NUMBER2 ...]
```

Optional arguments:
- `--headless`: Run in headless mode (no browser UI)
- `--output`: Choose output format (csv, json, or table)
- `--output-file`: Specify output file path

### Environment Variables

Set these environment variables for terminal access:
```bash
STO_USERNAME=your_username
STO_PASSWORD=your_password
OICT_USERNAME=your_username
OICT_PASSWORD=your_password
```

## 2. WMS Integration Script

Automates warehouse management operations by integrating with the warehouse management system (WMS):

### Features

- Automated inbound container processing
- Automated outbound container processing
- Eliminates manual data entry
- Prevents duplicate entries
- Streamlines warehouse operations

### Requirements

- Python 3.6+
- Chrome WebDriver
- Required Python packages:
  ```
  selenium
  pandas
  tabulate
  logging
  ```

### Installation

1. Clone the repository:
```bash
git clone [repository_url]
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Set up environment variables for terminal access

### Common Issues & Solutions

1. **Recaptcha Handling**: 
   - For Trapac terminal, manual verification might be required
   - The script will wait up to 5 minutes for verification completion

2. **Privacy Policy Popups**: 
   - Automated handling for most cases
   - Manual intervention might be needed in some instances

### Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

### License
This script uses the MIT License.  


### Support

For support, please open an issue in the repository or contact [your contact information].
