document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM fully loaded - Initializing app.js");
    
    // Initialize Mermaid
    mermaid.initialize({
        startOnLoad: true,
        theme: 'neutral',
        securityLevel: 'loose',
        flowchart: {
            useMaxWidth: true,
            htmlLabels: true,
            curve: 'basis'
        }
    });

    // DOM Elements
    const fileInput = document.getElementById('fileInput');
    const fileName = document.getElementById('fileName');
    const runSimulation = document.getElementById('runSimulation');
    const reportOutput = document.getElementById('reportOutput');
    const copyReport = document.getElementById('copyReport');
    const connectionStatus = document.getElementById('connectionStatus');
    const statusIndicator = connectionStatus.querySelector('.status-indicator');
    const statusText = connectionStatus.querySelector('.status-text');
    const fetchDirectButton = document.getElementById('fetchDirectButton');
    
    // Verify DOM elements are found
    console.log("DOM Elements found:", {
        fileInput: !!fileInput,
        fileName: !!fileName,
        runSimulation: !!runSimulation,
        reportOutput: !!reportOutput,
        copyReport: !!copyReport,
        connectionStatus: !!connectionStatus,
        statusIndicator: !!statusIndicator,
        statusText: !!statusText,
        fetchDirectButton: !!fetchDirectButton
    });
    
    // Get run ID input and manual fetch button
    const runIdInput = document.getElementById('runIdInput');
    
    // Variables
    let patientCaseFile = null;
    let currentRunId = null;
    let eventSource = null;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    const reconnectDelay = 1000; // Start with 1 second
    const apiBase = '/api'; // Base API URL
    let reportReceived = false; // Track if we've received a report

    // Event listeners for UI interactions
    fileInput.addEventListener('change', handleFileSelection);
    runSimulation.addEventListener('click', startSimulation);
    copyReport.addEventListener('click', copyReportToClipboard);
    fetchDirectButton.addEventListener('click', fetchReportDirectly);

    // File drag and drop enhancements
    const fileInputLabel = document.querySelector('.file-input-label');
    const fileDropArea = document.querySelector('.file-input-container');
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        fileDropArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        fileDropArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        fileDropArea.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        fileDropArea.classList.add('highlight');
    }
    
    function unhighlight() {
        fileDropArea.classList.remove('highlight');
    }
    
    fileDropArea.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length) {
            fileInput.files = files;
            handleFileSelection({ target: fileInput });
        }
    }

    // Handle file selection
    function handleFileSelection(event) {
        const file = event.target.files[0];
        if (file) {
            // Check if it's a JSON file
            if (file.type !== 'application/json' && !file.name.endsWith('.json')) {
                showMessage('Please select a JSON file', 'error');
                fileInput.value = '';
                fileName.textContent = 'No file selected';
                patientCaseFile = null;
                runSimulation.disabled = true;
                return;
            }
            
            fileName.textContent = file.name;
            patientCaseFile = file;
            runSimulation.disabled = false;
        } else {
            fileName.textContent = 'No file selected';
            patientCaseFile = null;
            runSimulation.disabled = true;
        }
    }

    // Start simulation
    async function startSimulation() {
        if (!patientCaseFile) {
            showMessage('Please select a patient case file first', 'error');
            return;
        }

        try {
            // Disable button during processing
            runSimulation.disabled = true;
            runSimulation.textContent = 'Processing...';
            
            // Reset report received flag
            reportReceived = false;
            
            // Create form data
            const formData = new FormData();
            formData.append('file', patientCaseFile);
            
            // Send request to API
            const response = await fetch(`${apiBase}/simulate`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to start simulation');
            }
            
            const data = await response.json();
            currentRunId = data.run_id;
            console.log(`===> SIMULATION STARTED WITH RUN ID: ${currentRunId}`);
            
            // Update the runIdInput with the current run_id
            if (runIdInput) {
                runIdInput.value = currentRunId;
            }
            
            // Connect to SSE stream
            connectSSE(currentRunId);
            
            // Update UI to show simulation is running
            reportOutput.textContent = 'Simulation in progress...';
            
        } catch (error) {
            console.error('Error:', error);
            showMessage(`Error: ${error.message}`, 'error');
            runSimulation.disabled = false;
            runSimulation.textContent = 'Run Simulation';
        }
    }

    // Copy report to clipboard
    function copyReportToClipboard() {
        navigator.clipboard.writeText(reportOutput.textContent)
            .then(() => {
                // Visual feedback
                const originalText = copyReport.textContent;
                copyReport.textContent = 'Copied!';
                setTimeout(() => {
                    copyReport.textContent = originalText;
                }, 2000);
            })
            .catch(err => {
                console.error('Failed to copy report:', err);
                showMessage('Failed to copy report to clipboard', 'error');
            });
    }

    // Connect to SSE stream
    function connectSSE(runId) {
        // Close existing connection if any
        if (eventSource) {
            eventSource.close();
        }
        
        // Update connection status
        updateConnectionStatus('connecting', 'Connecting...');
        
        // Create new EventSource connection
        const url = `${apiBase}/stream/${runId}`;
        console.log(`===> Connecting to SSE stream: ${url}`);
        eventSource = new EventSource(url);
        
        // Event handlers
        eventSource.onopen = () => {
            console.log("===> SSE connection opened");
            updateConnectionStatus('connected', 'Connected');
            reconnectAttempts = 0; // Reset reconnect counter on successful connection
        };
        
        // Log all message events
        eventSource.onmessage = (event) => {
            console.log(`===> SSE generic message received:`, event);
        };
        
        eventSource.addEventListener('status_update', (event) => {
            console.log("===> RECEIVED STATUS_UPDATE EVENT:", event);
            try {
                const statusData = JSON.parse(event.data);
                console.log("===> PARSED STATUS DATA:", statusData);
                updateWorkflowVisualization(statusData);
                
                // Check if this is the final status update
                if (statusData.status === "DONE" && statusData.message === "MDT Simulation Finished Successfully") {
                    console.log("===> SIMULATION FINISHED, WILL TRY AUTO-FETCHING REPORT IN 2 SECONDS");
                    // Wait a bit then try to auto-fetch the report if it's not received via SSE
                    setTimeout(() => {
                        if (!reportReceived && currentRunId) {
                            console.log("===> AUTO-FETCHING REPORT AFTER COMPLETION");
                            fetchReportDirectly();
                        }
                    }, 2000);
                }
            } catch (error) {
                console.error('Error parsing status update:', error);
            }
        });
        
        // Variables for storing chunked report data
        let reportChunks = {};
        let currentReportMetadata = null;
        
        // Handle the report metadata
        eventSource.addEventListener('report_metadata', (event) => {
            console.log("===> RECEIVED REPORT_METADATA EVENT:", event);
            try {
                const metadata = JSON.parse(event.data);
                console.log("===> PARSED REPORT METADATA:", metadata);
                currentReportMetadata = metadata;
                reportChunks = {}; // Reset chunks for new report
                reportOutput.textContent = `Receiving report data (0/${metadata.chunks} chunks)...`;
            } catch (error) {
                console.error('Error parsing report metadata:', error);
            }
        });
        
        // Handle report chunks
        eventSource.addEventListener('report_chunk', (event) => {
            console.log("===> RECEIVED REPORT_CHUNK EVENT:", event);
            try {
                const chunkData = JSON.parse(event.data);
                console.log("===> RECEIVED CHUNK INDEX:", chunkData.chunk_index);
                const { chunk_index, total_chunks, data } = chunkData;
                
                // Store this chunk
                reportChunks[chunk_index] = data;
                
                // Update progress
                const receivedChunks = Object.keys(reportChunks).length;
                reportOutput.textContent = `Receiving report data (${receivedChunks}/${total_chunks} chunks)...`;
                
                // Check if we have all chunks
                if (receivedChunks === total_chunks) {
                    // Reassemble the report
                    const completeData = [];
                    for (let i = 0; i < total_chunks; i++) {
                        if (reportChunks[i]) {
                            completeData.push(reportChunks[i]);
                        } else {
                            console.error(`Missing chunk ${i} of report`);
                            reportOutput.textContent = 'Error: Missing chunks in report data.';
                            return;
                        }
                    }
                    
                    // Parse and display the complete report
                    const fullReportJson = completeData.join('');
                    try {
                        const reportData = JSON.parse(fullReportJson);
                        console.log("===> REASSEMBLED REPORT:", reportData);
                        displayReport(reportData);
                        reportReceived = true; // Mark report as received
                        runSimulation.disabled = false;
                        runSimulation.textContent = 'Run Simulation';
                    } catch (jsonError) {
                        console.error('Error parsing reassembled JSON:', jsonError);
                        reportOutput.textContent = 'Error: Failed to reassemble report data.';
                    }
                }
            } catch (error) {
                console.error('Error processing report chunk:', error);
            }
        });
        
        eventSource.addEventListener('report', (event) => {
            console.log("===> RECEIVED REPORT EVENT:", event);
            try {
                // Log the raw event data
                console.log("===> RAW REPORT DATA:", event.data);
                const reportData = JSON.parse(event.data);
                console.log("===> PARSED REPORT DATA:", reportData);
                
                // Display the keys in the report data
                if (reportData && typeof reportData === 'object') {
                    console.log("===> REPORT KEYS:", Object.keys(reportData));
                }
                
                displayReport(reportData);
                reportReceived = true; // Mark report as received
                runSimulation.disabled = false;
                runSimulation.textContent = 'Run Simulation';
            } catch (error) {
                console.error('Error parsing report:', error);
                // Try to display the raw report data if parsing fails
                reportOutput.textContent = `Error parsing report JSON. Raw data: ${event.data}`;
                runSimulation.disabled = false;
                runSimulation.textContent = 'Run Simulation';
            }
        });
        
        eventSource.addEventListener('error', (event) => {
            console.error("===> SSE ERROR EVENT:", event);
            handleSSEError(event, runId);
        });
        
        eventSource.addEventListener('complete', (event) => {
            console.log("===> RECEIVED COMPLETE EVENT:", event);
            // Simulation completed, close connection
            eventSource.close();
            updateConnectionStatus('', 'Simulation completed');
            runSimulation.disabled = false;
            runSimulation.textContent = 'Run Simulation';
            
            // If no report was received, show a message
            if (!reportReceived) {
                console.log("===> No report received via SSE stream");
                reportOutput.textContent += '\n\nNo report was received via SSE stream. Click "Fetch Report Directly" to retrieve it.';
            }
        });
        
        // Log ping events
        eventSource.addEventListener('ping', (event) => {
            console.log("===> PING EVENT:", event);
        });
    }

    // Handle SSE connection errors
    function handleSSEError(event, runId) {
        console.error('SSE connection error:', event);
        
        // Update status
        updateConnectionStatus('error', 'Connection lost');
        
        // Close the errored connection
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
        
        // Implement exponential backoff for reconnection
        if (reconnectAttempts < maxReconnectAttempts) {
            const delay = reconnectDelay * Math.pow(2, reconnectAttempts);
            reconnectAttempts++;
            
            updateConnectionStatus('error', `Reconnecting in ${delay/1000}s... (${reconnectAttempts}/${maxReconnectAttempts})`);
            
            setTimeout(() => {
                connectSSE(runId);
            }, delay);
        } else {
            updateConnectionStatus('error', 'Failed to reconnect');
            showMessage('Connection to the server was lost and could not be re-established.', 'error');
            runSimulation.disabled = false;
            runSimulation.textContent = 'Run Simulation';
            
            // If no report was received, try to fetch it directly
            if (!reportReceived && currentRunId) {
                console.log("===> Auto-fetching report after connection failure");
                setTimeout(fetchReportDirectly, 1000);
            }
        }
    }

    // Update connection status helper
    function updateConnectionStatus(state, message) {
        statusIndicator.className = state ? `status-indicator ${state}` : 'status-indicator';
        statusText.textContent = message;
    }

    // Show message helper
    function showMessage(message, type = 'info') {
        // You could implement a toast or notification system here
        console.log(`MESSAGE (${type}): ${message}`);
        if (type === 'error') {
            alert(message);
        }
    }

    // Update workflow visualization based on status updates
    function updateWorkflowVisualization(statusData) {
        // Get the current mermaid graph
        const mermaidGraph = document.getElementById('mermaidGraph');
        
        // Basic mermaid graph structure
        let graphDefinition = `graph TD\n`;
        
        // Add nodes for each agent
        const agents = ['coordinator', 'ehr', 'imaging', 'pathology', 'guideline', 'specialist', 'evaluation'];
        const agentLabels = {
            'coordinator': 'Coordinator',
            'ehr': 'EHR Agent',
            'imaging': 'Imaging Agent',
            'pathology': 'Pathology Agent',
            'guideline': 'Guideline Agent',
            'specialist': 'Specialist Agent',
            'evaluation': 'Evaluation Agent'
        };
        
        agents.forEach(agent => {
            const isActive = statusData.agent_id.toLowerCase() === agent;
            const hasError = statusData.status === 'ERROR' && statusData.agent_id.toLowerCase() === agent;
            
            // Determine node class
            let nodeClass = '';
            if (isActive) nodeClass = 'class="active"';
            if (hasError) nodeClass = 'class="error"';
            
            // Add node with appropriate class
            graphDefinition += `    ${agent}${nodeClass}("${agentLabels[agent]}")\n`;
        });
        
        // Add connections
        graphDefinition += `    coordinator --> ehr\n`;
        graphDefinition += `    coordinator --> imaging\n`;
        graphDefinition += `    coordinator --> pathology\n`;
        graphDefinition += `    coordinator --> guideline\n`;
        graphDefinition += `    coordinator --> specialist\n`;
        graphDefinition += `    coordinator --> evaluation\n`;
        
        // Add status message at the bottom
        if (statusData.message) {
            // Escape any quotes in the message to prevent mermaid syntax errors
            const safeMessage = statusData.message.replace(/"/g, '\'');
            graphDefinition += `    status("${safeMessage}")\n`;
            graphDefinition += `    style status fill:#f8f9fa,stroke:none\n`;
        }
        
        // Update the mermaid diagram
        mermaidGraph.textContent = graphDefinition;
        
        // Re-render with mermaid
        mermaid.render('graphDiv', graphDefinition).then(result => {
            mermaidGraph.innerHTML = result.svg;
        }).catch(error => {
            console.error('Error rendering mermaid graph:', error);
        });
    }

    // Display the MDT report
    function displayReport(reportData) {
        // Format the JSON with indentation
        const formattedReport = JSON.stringify(reportData, null, 2);
        reportOutput.textContent = formattedReport;
        
        // Enable copy button
        copyReport.disabled = false;
        
        // Scroll to report
        reportOutput.scrollIntoView({ behavior: 'smooth' });
    }

    // Function to fetch report directly via REST API
    async function fetchReportDirectly() {
        const runId = currentRunId || (runIdInput ? runIdInput.value : null);
        
        if (!runId) {
            showMessage('No simulation run ID available', 'error');
            return;
        }
        
        try {
            fetchDirectButton.textContent = 'Fetching...';
            fetchDirectButton.disabled = true;
            
            console.log(`===> FETCHING REPORT DIRECTLY FOR RUN ID: ${runId}`);
            const response = await fetch(`${apiBase}/report/${runId}`);
            
            if (!response.ok) {
                throw new Error(`Failed to fetch report: ${response.statusText}`);
            }
            
            const reportData = await response.json();
            console.log("===> DIRECT FETCH REPORT DATA:", reportData);
            
            displayReport(reportData);
            fetchDirectButton.textContent = 'Report Fetched Successfully';
            setTimeout(() => {
                fetchDirectButton.textContent = 'Fetch Report Directly';
                fetchDirectButton.disabled = false;
            }, 3000);
            
        } catch (error) {
            console.error('Error fetching report directly:', error);
            fetchDirectButton.textContent = 'Fetch Report Directly';
            fetchDirectButton.disabled = false;
            showMessage(`Error: ${error.message}`, 'error');
        }
    }

    // Log initialization complete
    console.log("App.js initialization complete");
}); 