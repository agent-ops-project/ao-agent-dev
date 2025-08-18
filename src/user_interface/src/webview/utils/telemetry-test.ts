// Temporary test utility for telemetry debugging
import { trackExperimentClick, trackNodeInputOutputView, telemetryClient } from './telemetry';

declare global {
  interface Window {
    testTelemetry: () => void;
    telemetryClient: any;
  }
}

// Make telemetry functions available globally for testing
window.testTelemetry = async () => {
  console.log('🧪 Starting telemetry test...');
  
  try {
    // Test experiment click
    console.log('Testing experiment click...');
    const result1 = await trackExperimentClick('test_experiment', 'test_session_123');
    console.log('Experiment click result:', result1);
    
    // Test node input view
    console.log('Testing node input view...');
    const result2 = await trackNodeInputOutputView('test_node_456', 'input', 'test_session_123', 'test_node_type');
    console.log('Node input view result:', result2);
    
    // Test node output view  
    console.log('Testing node output view...');
    const result3 = await trackNodeInputOutputView('test_node_789', 'output', 'test_session_123', 'test_node_type');
    console.log('Node output view result:', result3);
    
    console.log('🧪 Telemetry test completed!');
    
  } catch (error) {
    console.error('🚨 Telemetry test failed:', error);
  }
};

// Also expose the client for direct testing
window.telemetryClient = telemetryClient;

console.log('🧪 Telemetry test utilities loaded. Run window.testTelemetry() to test manually.'); 