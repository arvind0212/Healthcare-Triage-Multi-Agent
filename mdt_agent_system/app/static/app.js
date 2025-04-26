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
        },
        classDef: {
            active: {
                fill: '#28a745',
                stroke: '#1e7e34',
                color: '#fff',
                'font-weight': 'bold'
            },
            error: {
                fill: '#dc3545',
                stroke: '#bd2130',
                color: '#fff',
                'font-weight': 'bold'
            }
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
    
    // View toggling elements
    const jsonViewBtn = document.getElementById('jsonViewBtn');
    const markdownViewBtn = document.getElementById('markdownViewBtn');
    const jsonView = document.getElementById('jsonView');
    const markdownView = document.getElementById('markdownView');
    const markdownOutput = document.getElementById('markdownOutput');
    const copyMarkdown = document.getElementById('copyMarkdown');
    
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
        fetchDirectButton: !!fetchDirectButton,
        jsonViewBtn: !!jsonViewBtn,
        markdownViewBtn: !!markdownViewBtn,
        jsonView: !!jsonView,
        markdownView: !!markdownView,
        markdownOutput: !!markdownOutput,
        copyMarkdown: !!copyMarkdown
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
    copyMarkdown.addEventListener('click', copyMarkdownToClipboard);
    fetchDirectButton.addEventListener('click', fetchReportDirectly);
    jsonViewBtn.addEventListener('click', () => switchView('json'));
    markdownViewBtn.addEventListener('click', () => switchView('markdown'));

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

    // Copy markdown to clipboard
    function copyMarkdownToClipboard() {
        // Get the markdown as plain text without HTML formatting
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = markdownOutput.innerHTML;
        const markdownText = tempDiv.textContent || tempDiv.innerText || '';
        
        navigator.clipboard.writeText(markdownText)
            .then(() => {
                // Visual feedback
                const originalText = copyMarkdown.textContent;
                copyMarkdown.textContent = 'Copied!';
                setTimeout(() => {
                    copyMarkdown.textContent = originalText;
                }, 2000);
            })
            .catch(err => {
                console.error('Failed to copy markdown:', err);
                showMessage('Failed to copy markdown to clipboard', 'error');
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
        const agents = ['coordinator', 'ehr', 'imaging', 'pathology', 'guideline', 'specialist', 'evaluation', 'summary'];
        const agentLabels = {
            'coordinator': 'Coordinator',
            'ehr': 'EHR Agent',
            'imaging': 'Imaging Agent',
            'pathology': 'Pathology Agent',
            'guideline': 'Guideline Agent',
            'specialist': 'Specialist Agent',
            'evaluation': 'Evaluation Agent',
            'summary': 'Summary Agent'
        };
        
        agents.forEach(agent => {
            const isActive = statusData.agent_id.toLowerCase() === agent;
            const hasError = statusData.status === 'ERROR' && statusData.agent_id.toLowerCase() === agent;
            
            // Add node with appropriate class using Mermaid's ::: class syntax
            graphDefinition += `    ${agent}["${agentLabels[agent]}"]`;
            
            // Apply class using ::: syntax
            if (isActive) graphDefinition += `:::active`;
            if (hasError) graphDefinition += `:::error`;
            
            graphDefinition += `\n`;
        });
        
        // Add connections
        graphDefinition += `    coordinator --> ehr\n`;
        graphDefinition += `    coordinator --> imaging\n`;
        graphDefinition += `    coordinator --> pathology\n`;
        graphDefinition += `    coordinator --> guideline\n`;
        graphDefinition += `    coordinator --> specialist\n`;
        graphDefinition += `    coordinator --> evaluation\n`;
        graphDefinition += `    coordinator --> summary\n`;
        
        // Add status message at the bottom
        if (statusData.message) {
            // Escape any quotes in the message to prevent mermaid syntax errors
            const safeMessage = statusData.message.replace(/"/g, '\'');
            graphDefinition += `    status["${safeMessage}"]\n`;
            graphDefinition += `    style status fill:#f8f9fa,stroke:none\n`;
        }
        
        // Add class definitions
        graphDefinition += `    classDef active fill:#28a745,stroke:#1e7e34,color:#fff,font-weight:bold;\n`;
        graphDefinition += `    classDef error fill:#dc3545,stroke:#bd2130,color:#fff,font-weight:bold;\n`;
        
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
    function displayReport(data) {
        if (!data) {
            reportOutput.textContent = 'No report data available';
            return;
        }
        
        console.log('Displaying report:', data);
        
        try {
            // Handle markdown summary if available
            if (data.markdown_summary) {
                // Create a section for the markdown summary at the top
                const summaryDiv = document.createElement('div');
                summaryDiv.id = 'mdt-summary';
                summaryDiv.className = 'mdt-summary';
                summaryDiv.innerHTML = markdownToHtml(data.markdown_summary);
                
                // Insert the summary at the top of the report output area
                if (markdownView.firstChild) {
                    markdownView.insertBefore(summaryDiv, markdownView.firstChild);
                } else {
                    markdownView.appendChild(summaryDiv);
                }
                
                // Automatically switch to markdown view when summary is available
                switchView('markdown');
            }
            
            // Format the JSON for display
            const formattedJson = JSON.stringify(data, null, 2);
            reportOutput.textContent = formattedJson;
            
            // Format as Markdown
            const markdownHtml = data.markdown_summary || convertJsonToMarkdown(data);
            markdownOutput.innerHTML = markdownHtml;
            
            // Show the copy buttons
            copyReport.style.display = 'block';
            copyMarkdown.style.display = 'block';
            
            // Mark report as received
            reportReceived = true;
            
        } catch (error) {
            console.error('Error formatting report:', error);
            reportOutput.textContent = `Error formatting report: ${error.message}\n\nRaw data: ${JSON.stringify(data)}`;
        }
    }

    // Switch between JSON and Markdown views
    function switchView(viewType) {
        if (viewType === 'json') {
            jsonView.style.display = 'block';
            markdownView.style.display = 'none';
            jsonViewBtn.classList.add('active');
            markdownViewBtn.classList.remove('active');
        } else {
            jsonView.style.display = 'none';
            markdownView.style.display = 'block';
            jsonViewBtn.classList.remove('active');
            markdownViewBtn.classList.add('active');
        }
    }

    // Convert JSON to Markdown
    function convertJsonToMarkdown(data) {
        if (!data) return 'No data available';
        
        let markdown = `# MDT Report for Patient ${data.patient_id || 'Unknown'}\n\n`;
        
        // Add summary
        if (data.summary) {
            markdown += `## Summary\n${data.summary}\n\n`;
        }
        
        // Add EHR Analysis
        if (data.ehr_analysis) {
            markdown += `## EHR Analysis\n`;
            if (typeof data.ehr_analysis === 'object') {
                Object.keys(data.ehr_analysis).forEach(key => {
                    const value = data.ehr_analysis[key];
                    if (typeof value === 'object') {
                        markdown += `### ${formatTitle(key)}\n`;
                        if (Array.isArray(value)) {
                            value.forEach(item => {
                                if (typeof item === 'object') {
                                    Object.keys(item).forEach(itemKey => {
                                        markdown += `- **${formatTitle(itemKey)}**: ${item[itemKey]}\n`;
                                    });
                                } else {
                                    markdown += `- ${item}\n`;
                                }
                            });
                        } else {
                            Object.keys(value).forEach(subKey => {
                                markdown += `- **${formatTitle(subKey)}**: ${value[subKey]}\n`;
                            });
                        }
                        markdown += '\n';
                    } else {
                        markdown += `### ${formatTitle(key)}\n${value}\n\n`;
                    }
                });
            } else {
                markdown += data.ehr_analysis + '\n\n';
            }
        }
        
        // Add Imaging Analysis
        if (data.imaging_analysis) {
            markdown += `## Imaging Analysis\n`;
            if (typeof data.imaging_analysis === 'object') {
                Object.keys(data.imaging_analysis).forEach(key => {
                    const value = data.imaging_analysis[key];
                    if (typeof value === 'object') {
                        markdown += `### ${formatTitle(key)}\n`;
                        if (Array.isArray(value)) {
                            value.forEach(item => {
                                if (typeof item === 'object') {
                                    Object.keys(item).forEach(itemKey => {
                                        markdown += `- **${formatTitle(itemKey)}**: ${item[itemKey]}\n`;
                                    });
                                } else {
                                    markdown += `- ${item}\n`;
                                }
                            });
                        } else {
                            Object.keys(value).forEach(subKey => {
                                markdown += `- **${formatTitle(subKey)}**: ${value[subKey]}\n`;
                            });
                        }
                        markdown += '\n';
                    } else {
                        markdown += `### ${formatTitle(key)}\n${value}\n\n`;
                    }
                });
            } else {
                markdown += data.imaging_analysis + '\n\n';
            }
        }
        
        // Add Pathology Analysis
        if (data.pathology_analysis) {
            markdown += `## Pathology Analysis\n`;
            if (typeof data.pathology_analysis === 'object') {
                Object.keys(data.pathology_analysis).forEach(key => {
                    const value = data.pathology_analysis[key];
                    if (typeof value === 'object') {
                        markdown += `### ${formatTitle(key)}\n`;
                        if (Array.isArray(value)) {
                            value.forEach(item => {
                                if (typeof item === 'object') {
                                    Object.keys(item).forEach(itemKey => {
                                        markdown += `- **${formatTitle(itemKey)}**: ${item[itemKey]}\n`;
                                    });
                                } else {
                                    markdown += `- ${item}\n`;
                                }
                            });
                        } else {
                            Object.keys(value).forEach(subKey => {
                                markdown += `- **${formatTitle(subKey)}**: ${value[subKey]}\n`;
                            });
                        }
                        markdown += '\n';
                    } else {
                        markdown += `### ${formatTitle(key)}\n${value}\n\n`;
                    }
                });
            } else {
                markdown += data.pathology_analysis + '\n\n';
            }
        }
        
        // Add Guideline Recommendations
        if (data.guideline_recommendations && Array.isArray(data.guideline_recommendations)) {
            markdown += `## Guideline Recommendations\n`;
            data.guideline_recommendations.forEach((rec, index) => {
                markdown += `### Recommendation ${index + 1}\n`;
                if (typeof rec === 'object') {
                    Object.keys(rec).forEach(key => {
                        if (key !== 'source_details' || rec.source_details) {
                            markdown += `- **${formatTitle(key)}**: ${formatValue(rec[key])}\n`;
                        }
                    });
                } else {
                    markdown += `${rec}\n`;
                }
                markdown += '\n';
            });
        }
        
        // Add Specialist Assessment
        if (data.specialist_assessment) {
            markdown += `## Specialist Assessment\n`;
            if (typeof data.specialist_assessment === 'object') {
                Object.keys(data.specialist_assessment).forEach(key => {
                    const value = data.specialist_assessment[key];
                    if (typeof value === 'object') {
                        markdown += `### ${formatTitle(key)}\n`;
                        if (Array.isArray(value)) {
                            value.forEach(item => {
                                if (typeof item === 'object') {
                                    Object.keys(item).forEach(itemKey => {
                                        markdown += `- **${formatTitle(itemKey)}**: ${item[itemKey]}\n`;
                                    });
                                } else {
                                    markdown += `- ${item}\n`;
                                }
                            });
                        } else {
                            Object.keys(value).forEach(subKey => {
                                markdown += `- **${formatTitle(subKey)}**: ${value[subKey]}\n`;
                            });
                        }
                        markdown += '\n';
                    } else {
                        markdown += `### ${formatTitle(key)}\n${value}\n\n`;
                    }
                });
            } else {
                markdown += data.specialist_assessment + '\n\n';
            }
        }
        
        // Add Treatment Options
        if (data.treatment_options && Array.isArray(data.treatment_options)) {
            markdown += `## Treatment Options\n`;
            data.treatment_options.forEach((option, index) => {
                markdown += `### Option ${index + 1}: ${option.name || ''}\n`;
                if (typeof option === 'object') {
                    Object.keys(option).forEach(key => {
                        if (key !== 'name') {
                            const value = option[key];
                            if (Array.isArray(value)) {
                                markdown += `#### ${formatTitle(key)}\n`;
                                value.forEach(item => {
                                    markdown += `- ${item}\n`;
                                });
                                markdown += '\n';
                            } else if (typeof value === 'object') {
                                markdown += `#### ${formatTitle(key)}\n`;
                                Object.keys(value).forEach(subKey => {
                                    markdown += `- **${formatTitle(subKey)}**: ${value[subKey]}\n`;
                                });
                                markdown += '\n';
                            } else {
                                markdown += `- **${formatTitle(key)}**: ${value}\n`;
                            }
                        }
                    });
                } else {
                    markdown += `${option}\n`;
                }
                markdown += '\n';
            });
        }
        
        // Add Evaluation
        if (data.evaluation_score !== undefined || data.evaluation_comments) {
            markdown += `## Evaluation\n`;
            if (data.evaluation_score !== undefined) {
                markdown += `- **Score**: ${data.evaluation_score}\n`;
            }
            if (data.evaluation_comments) {
                markdown += `- **Comments**: ${data.evaluation_comments}\n`;
            }
            markdown += '\n';
        }
        
        // Add metadata
        markdown += `---\n`;
        markdown += `Generated on: ${data.timestamp ? new Date(data.timestamp).toLocaleString() : new Date().toLocaleString()}\n`;
        
        // Convert the markdown to HTML for display
        return markdownToHtml(markdown);
    }
    
    // Helper function to format titles
    function formatTitle(str) {
        if (!str) return '';
        return str
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase());
    }
    
    // Helper function to format values
    function formatValue(value) {
        if (value === null || value === undefined) return '';
        if (typeof value === 'object') {
            if (Array.isArray(value)) {
                return value.join(', ');
            } else {
                return JSON.stringify(value);
            }
        }
        return value.toString();
    }
    
    // Convert markdown to HTML - Enhanced for better rendering
    function markdownToHtml(markdown) {
        if (!markdown) return '';
        
        // Basic markdown to HTML conversion with improvements
        return markdown
            // Headers
            .replace(/^# (.*$)/gm, '<h1>$1</h1>')
            .replace(/^## (.*$)/gm, '<h2>$1</h2>')
            .replace(/^### (.*$)/gm, '<h3>$1</h3>')
            .replace(/^#### (.*$)/gm, '<h4>$1</h4>')
            
            // Bold
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            
            // Italic
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            
            // Checkbox lists (for Critical Next Steps)
            .replace(/^\s*- \[ \] (.*$)/gm, '<li class="task-list-item"><input type="checkbox" disabled> $1</li>')
            .replace(/^\s*- \[x\] (.*$)/gm, '<li class="task-list-item"><input type="checkbox" checked disabled> $1</li>')
            
            // Regular lists
            .replace(/^\s*- (.*$)/gm, '<li>$1</li>')
            .replace(/(<li.*>.*<\/li>\n)+/g, '<ul>$&</ul>')
            
            // Numbered lists
            .replace(/^\s*\d+\.\s+(.*$)/gm, '<li>$1</li>')
            .replace(/(<li>.*<\/li>\n)+/g, '<ol>$&</ol>')
            
            // Paragraphs
            .replace(/^(?!<[holu]|<strong|<em)(.*$)/gm, function(match) {
                return match.trim() ? '<p>' + match + '</p>' : '';
            })
            
            // Fix empty lines between list items
            .replace(/<\/ul>\n<ul>/g, '')
            .replace(/<\/ol>\n<ol>/g, '')
            
            // Line breaks
            .replace(/\n/g, '<br>');
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