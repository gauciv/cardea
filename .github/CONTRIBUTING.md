# Contributing to Cardea

Thank you for your interest in contributing to Cardea! 🛡️

Cardea is a localized network threat detection agent designed to bring enterprise-grade security to small businesses without IT teams. This document provides guidelines for contributing to the project. By participating, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## 📋 Table of Contents
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Security Considerations](#security-considerations)
- [Community](#community)

---

## 🚀 Getting Started

### Prerequisites
- **Edge Device**: Raspberry Pi 4+ or ThinkPad (for edge deployment)
- **Python 3.9+** or **Node.js 18+** (depending on component)
- **Azure Account**: For Azure AI Foundry integration
- **Docker** (recommended for containerized deployment)
- **Git**: For version control

### First Time Setup

1. **Fork the repository**
   ```bash
   # Click "Fork" on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/cardea.git
   cd cardea
   ```

2. **Add upstream remote**
   ```bash
   git remote add upstream https://github.com/ORIGINAL_REPO/cardea.git
   ```

3. **Install dependencies**
   ```bash
   # Edge AI Agent
   cd edge-agent
   pip install -r requirements.txt
   
   # Dashboard (if working on frontend)
   cd ../dashboard
   npm install
   ```

4. **Configure your environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Azure AI Foundry credentials
   # Add network interface configuration
   ```

5. **Verify setup**
   ```bash
   # Run tests
   pytest
   # Or: npm test (for frontend)
   ```

---

## 💻 Development Setup

### Running Locally

**Edge AI Agent:**
```bash
cd edge-agent
python main.py --dev-mode
# Monitors local network traffic patterns
```

**Cloud Threat Analysis Service:**
```bash
cd cloud-service
python app.py
# Runs threat analysis API
```

**Dashboard:**
```bash
cd dashboard
npm run dev
# Runs on http://localhost:3000
```

### Project Structure
```
cardea/
├── edge-agent/              # Edge AI monitoring agent
│   ├── packet_capture/      # Network packet monitoring
│   ├── anomaly_detection/   # Local ML-based anomaly detection
│   ├── log_processor/       # Log snippet processing
│   └── azure_client/        # Azure AI Foundry integration
├── cloud-service/           # Cloud-based threat analysis
│   ├── ai_analysis/         # Deep-dive threat assessment
│   ├── firewall_patcher/    # Automated firewall rules
│   └── report_generator/    # Human-readable reports
├── dashboard/               # Accessibility-focused dashboard
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   └── accessibility/   # High-readability features
├── iot-profiles/            # Device profiles (printers, cameras)
├── tests/                   # Comprehensive test suite
└── docs/                    # Documentation
```

---

## 🤝 How to Contribute

### Areas We Need Help With

#### 🐛 Bug Fixes
- Check [open issues](../../issues?q=is%3Aissue+is%3Aopen+label%3Abug)
- Look for issues tagged with `good first issue`
- Focus on edge device compatibility issues

#### ✨ New Features
- **IoT Device Profiles**: Add support for new device types
- **Threat Detection Models**: Improve ML anomaly detection
- **Accessibility Features**: Enhance dashboard readability
- **Firewall Integration**: Support for additional firewall vendors

#### 📝 Documentation
- Deployment guides for different edge devices
- IoT device configuration tutorials
- Security best practices
- MSP integration guides

#### 🧪 Testing
- Network traffic simulation scenarios
- Edge device testing on various hardware
- Accessibility testing (screen readers, high contrast)
- Integration testing with Azure AI Foundry

#### 🎨 UI/UX
- High-readability font implementations
- Simplified security visualizations
- Accessible color schemes
- Mobile-responsive dashboard

#### 🔒 Security
- Threat detection algorithm improvements
- False positive reduction
- Security audit of edge-to-cloud communication

### Finding Issues to Work On

**Labels to look for:**
- `good first issue` - Great for newcomers
- `help wanted` - Community contributions welcome
- `edge-device` - Edge AI agent improvements
- `accessibility` - Dashboard accessibility features
- `iot-support` - IoT device profile additions
- `ml-model` - Machine learning improvements
- `documentation` - Documentation improvements

---

## 📏 Coding Standards

### Python (Edge Agent & Cloud Service)
```python
# Follow PEP 8
# Use type hints
def analyze_packet(packet: NetworkPacket) -> ThreatScore:
    """
    Analyze network packet for anomalies.
    
    Args:
        packet: The network packet to analyze
        
    Returns:
        ThreatScore: Anomaly score and classification
    """
    pass

# Use descriptive variable names
is_suspicious_activity = check_pattern(packet)

# Comment complex algorithms
# ML model expects normalized features between 0-1
features = normalize_features(raw_data)
```

### JavaScript/TypeScript (Dashboard)
```typescript
// Use TypeScript for type safety
interface ThreatAlert {
  severity: 'low' | 'medium' | 'high' | 'critical';
  deviceName: string;
  timestamp: Date;
  humanReadableDescription: string;
}

// Follow React best practices
// Use functional components and hooks
const ThreatDashboard: React.FC = () => {
  const [alerts, setAlerts] = useState<ThreatAlert[]>([]);
  // Component logic
};
```

### Code Style
- **Python**: Follow PEP 8, use Black formatter
- **JavaScript/TypeScript**: Follow Airbnb style guide, use ESLint + Prettier
- **Line length**: Max 88 characters (Python), 100 characters (JS/TS)
- **Comments**: Explain "why" not "what"
- **Accessibility**: WCAG 2.1 AA compliance for all UI components

---

## 🧪 Testing

### Writing Tests
```python
# Python tests (pytest)
def test_anomaly_detection():
    """Test that known attack patterns are detected."""
    attack_packet = create_malicious_packet()
    score = anomaly_detector.score(attack_packet)
    assert score.is_threat == True
    assert score.confidence > 0.8
```

```typescript
// TypeScript tests (Jest)
describe('ThreatDashboard', () => {
  it('displays high severity alerts prominently', () => {
    const { getByText } = render(<ThreatDashboard />);
    expect(getByText('Critical Threat Detected')).toBeInTheDocument();
  });
});
```

### Test Coverage
- Aim for >80% code coverage
- Unit tests for all ML models
- Integration tests for Azure AI Foundry communication
- E2E tests for dashboard workflows
- Accessibility tests using axe-core

### Running Tests
```bash
# Python
pytest tests/ --cov=edge-agent --cov-report=html

# JavaScript
npm test -- --coverage

# Accessibility tests
npm run test:a11y
```

---

## 📝 Documentation

### Code Documentation
- **Docstrings**: Required for all public functions/classes
- **Inline comments**: For complex logic, especially ML algorithms
- **README**: Update if adding new features or changing setup

### User Documentation
- **Setup guides**: For different edge devices (RPi, ThinkPad, etc.)
- **IoT device configuration**: How to add new device types
- **Troubleshooting**: Common issues and solutions
- **Security guidelines**: Best practices for deployment

### API Documentation
- Use OpenAPI/Swagger for REST APIs
- Document all Azure AI Foundry integration points
- Include example requests/responses

---

## 💾 Commit Guidelines

### Commit Message Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `security`: Security improvements
- `perf`: Performance improvements
- `a11y`: Accessibility improvements

**Examples:**
```bash
feat(edge-agent): add support for TP-Link camera detection

Implements packet pattern recognition for TP-Link smart cameras.
Includes baseline traffic profile and anomaly thresholds.

Closes #123

---

fix(dashboard): improve contrast ratio for threat severity indicators

Updates color palette to meet WCAG 2.1 AA standards.
Critical threats now use #DC2626 with white text.

Fixes #456

---

docs(setup): add Raspberry Pi 5 installation guide

Provides step-by-step instructions for RPi5 deployment
including GPIO configuration for status LED.
```

### Commit Best Practices
- Write clear, descriptive commit messages
- Keep commits atomic (one logical change per commit)
- Reference issues in commit messages
- Sign commits if possible (`git commit -S`)

---

## 🔄 Pull Request Process

### Before Submitting

1. **Update from upstream**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run tests locally**
   ```bash
   # All tests must pass
   pytest && npm test
   ```

3. **Check code style**
   ```bash
   black edge-agent/
   npm run lint
   ```

4. **Update documentation**
   - Update README if adding features
   - Add/update docstrings
   - Update CHANGELOG.md

### PR Checklist

- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings or errors
- [ ] I have added tests that prove my fix is effective or feature works
- [ ] New and existing unit tests pass locally
- [ ] I have checked accessibility (WCAG 2.1 AA) for UI changes
- [ ] I have not committed any API keys, credentials, or secrets
- [ ] I have tested on edge device hardware (if applicable)

### PR Review Process

1. **Automated Checks**: CI/CD will run tests and linters
2. **Code Review**: Maintainers will review your code
3. **Testing**: For hardware-specific changes, testing may be required
4. **Approval**: At least one maintainer approval required
5. **Merge**: Maintainer will merge after approval

---

## 🔒 Security Considerations

### Security Requirements

1. **No Hardcoded Secrets**
   - Use environment variables
   - Never commit API keys or credentials
   - Use Azure Key Vault for production secrets

2. **Secure Communication**
   - All edge-to-cloud communication must use TLS 1.3+
   - Implement certificate pinning
   - Encrypt sensitive log snippets before transmission

3. **Data Privacy**
   - Minimize PII in logs
   - Implement data retention policies
   - Comply with GDPR/CCPA requirements

4. **Edge Device Security**
   - Secure boot recommended
   - Regular security updates
   - Principle of least privilege

### Reporting Security Vulnerabilities

**DO NOT** create public issues for security vulnerabilities.

Instead, email: **security@cardea-project.example.com**

See [SECURITY.md](SECURITY.md) for details.

---

## 🌐 Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and community chat
- **Discord**: Real-time community support (if available)

### Getting Help

- Read the [Documentation](../docs/)
- Check [FAQ](../docs/FAQ.md)
- Search existing [Issues](../../issues)
- Ask in [Discussions](../../discussions)

### Recognition

Contributors will be:
- Listed in [CONTRIBUTORS.md](CONTRIBUTORS.md)
- Credited in release notes
- Acknowledged in project documentation

---

## 📜 License

By contributing to Cardea, you agree that your contributions will be licensed under the same license as the project (see [LICENSE](LICENSE) file).

---

## 🙏 Thank You!

Your contributions make Cardea better for everyone! Whether it's:
- A bug fix that helps MSPs monitor their clients
- An accessibility improvement for security teams
- A new IoT device profile for small businesses
- Documentation that helps someone deploy their first edge agent

Every contribution matters. Thank you for helping make enterprise-grade security accessible to small businesses! 🛡️✨
