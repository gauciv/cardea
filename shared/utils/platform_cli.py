#!/usr/bin/env python3
"""
Cardea Platform Detection CLI
Command-line interface for platform detection and configuration
"""

import sys
from pathlib import Path

# Add utils to path
sys.path.append(str(Path(__file__).parent))

from platform_detector import platform_detector
from environment_configurator import EnvironmentConfigurator

def main():
    """Main CLI entry point"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "report":
            # Generate full platform report
            configurator = EnvironmentConfigurator()
            print(configurator.generate_platform_report())
            
        elif command == "config":
            # Generate environment configuration
            configurator = EnvironmentConfigurator()
            config = configurator.generate_sentry_env()
            
            print("# Generated Environment Configuration")
            for key, value in config.items():
                print(f"{key}={value}")
                
        elif command == "validate":
            # Validate deployment environment
            validation = platform_detector.validate_environment()
            
            if validation["ready"]:
                print("✅ Platform ready for deployment")
                sys.exit(0)
            else:
                print("❌ Platform not ready for deployment")
                for error in validation["errors"]:
                    print(f"   Error: {error}")
                sys.exit(1)
                
        elif command == "interface":
            # Get recommended network interface
            recommended = platform_detector.get_recommended_interface()
            if recommended:
                print(recommended)
            else:
                print("No suitable interface found")
                sys.exit(1)
                
        else:
            print(f"Unknown command: {command}")
            print("Available commands: report, config, validate, interface")
            sys.exit(1)
    else:
        # Default: show platform report
        configurator = EnvironmentConfigurator()
        print(configurator.generate_platform_report())

if __name__ == "__main__":
    main()