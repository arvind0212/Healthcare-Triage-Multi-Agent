document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM fully loaded - Initializing app.js");
    
    // Initialize Mermaid with the updated configuration
    mermaid.initialize({
        startOnLoad: false,
        theme: 'base',
        securityLevel: 'loose',
        flowchart: {
            useMaxWidth: true,
            htmlLabels: true,
            curve: 'basis',
            diagramPadding: 8,
            nodeSpacing: 60,
            rankSpacing: 80,
            defaultRenderer: 'dagre-wrapper'
        },
        themeVariables: {
            fontFamily: 'Inter, sans-serif',
            fontSize: '14px',
            primaryTextColor: '#FFFFFF',
            lineColor: '#999999',
            mainBkg: '#F3F4F6',
            nodeBorder: '#E5E7EB',
            clusterBkg: 'transparent',
            clusterBorder: 'transparent',
            edgeLabelBackground: 'transparent'
        },
        parseError: function(err) {
            console.error('Mermaid parse error:', err);
            const diagramContainer = document.getElementById('workflowDiagram');
            if (diagramContainer) {
                diagramContainer.innerHTML = `
                    <details class="error-details">
                        <summary>Error rendering diagram</summary>
                        <p>${err}</p>
                        <pre></pre>
                    </details>
                `;
            }
        }
    });

    // DOM Elements
    const fileInput = document.getElementById('fileInput');
    const fileName = document.getElementById('fileName');
    const runSimulation = document.getElementById('runSimulation');
    const connectionStatus = document.getElementById('connectionStatus');
    const statusIndicator = connectionStatus.querySelector('.status-indicator');
    const statusText = connectionStatus.querySelector('.status-text');
    const markdownSummary = document.getElementById('markdownSummary');
    const agentOutputs = document.getElementById('agentOutputs');
    const copyMarkdown = document.getElementById('copyMarkdown');
    const runIdInput = document.getElementById('runIdInput');
    const manualFetchButton = document.getElementById('manualFetchButton');
    
    // Agent Map for node identification and display names
    const agentMap = {
        coordinator: { id: 'coordinator', name: 'Coordinator', icon: 'fa-sitemap' },
        ehr_agent: { id: 'ehr', name: 'EHR Agent', icon: 'fa-notes-medical' },
        imaging_agent: { id: 'imaging', name: 'Imaging Agent', icon: 'fa-x-ray' },
        pathology_agent: { id: 'pathology', name: 'Pathology Agent', icon: 'fa-microscope' },
        guideline_agent: { id: 'guideline', name: 'Guideline Agent', icon: 'fa-book-medical' },
        specialist_agent: { id: 'specialist', name: 'Specialist Agent', icon: 'fa-user-md' },
        evaluation_agent: { id: 'evaluation', name: 'Evaluation Agent', icon: 'fa-check-square' },
        summary_agent: { id: 'summary', name: 'Summary Agent', icon: 'fa-file-alt' }
    };
    
    // Node state storage
    let nodeStates = {};
    
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
    copyMarkdown.addEventListener('click', copyReportToClipboard);
    manualFetchButton.addEventListener('click', fetchReportManually);
    
    // Render initial diagram
    initializeVisualization();

    // File drag and drop enhancements
    const fileDropArea = document.querySelector('.file-input-container');
    
    if (fileDropArea) {
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
            if (fileDropArea) fileDropArea.classList.add('highlight');
        }
        
        function unhighlight() {
            if (fileDropArea) fileDropArea.classList.remove('highlight');
        }
        
        fileDropArea.addEventListener('drop', handleDrop, false);
    }
    
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
            runSimulation.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            
            // Reset report received flag
            reportReceived = false;
            
            // Reset visualization
            resetVisualization();
            
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
            markdownSummary.innerHTML = '<div class="loading">Simulation in progress...</div>';
            agentOutputs.innerHTML = '';
            
        } catch (error) {
            console.error('Error:', error);
            showMessage(`Error: ${error.message}`, 'error');
            runSimulation.disabled = false;
            runSimulation.innerHTML = '<i class="fas fa-play-circle"></i> Run Simulation';
        }
    }

    // Copy report to clipboard
    function copyReportToClipboard() {
        const summaryText = markdownSummary.textContent || '';
        
        navigator.clipboard.writeText(summaryText)
            .then(() => {
                // Visual feedback
                const originalText = copyMarkdown.textContent;
                copyMarkdown.textContent = 'Copied!';
                setTimeout(() => {
                    copyMarkdown.textContent = originalText;
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
            eventSource = null;
        }
        
        // Reset reconnect attempts
        reconnectAttempts = 0;
        
        // Create new EventSource - update URL to match backend
        const sseUrl = `${apiBase}/stream/${runId}`;
        console.log(`Connecting to SSE stream: ${sseUrl}`);
        
        eventSource = new EventSource(sseUrl);
        
        // Use specific event listeners for each event type
        eventSource.addEventListener('status_update', handleStatusUpdate);
        eventSource.addEventListener('report', handleReportEvent);
        eventSource.addEventListener('complete', handleCompleteEvent);
        
        // General message handler for any unlabeled events
        eventSource.onmessage = function(event) {
            console.log(`Generic SSE message received for ${runId}:`, event.data);
            
            try {
                const data = JSON.parse(event.data);
                
                // Check if it's a report
                if (data.status === 'REPORT' || data.type === 'report') {
                    displayReport(data.data || data);
                    return;
                }
                
                // Otherwise treat as status update
                updateWorkflowVisualization(data);
                
            } catch (error) {
                console.error('Error parsing SSE message:', error);
            }
        };
        
        // Connection established
        eventSource.onopen = function() {
            console.log(`SSE connection established for ${runId}`);
            updateConnectionStatus('connected', 'Connected to simulation');
        };
        
        // Handle errors
        eventSource.onerror = function(event) {
            handleSSEError(event, runId);
        };
    }
    
    // Handle specific status update events
    function handleStatusUpdate(event) {
        console.log('Status update received:', event.data);
        try {
            const data = JSON.parse(event.data);
            console.log('Parsed status update data:', data);
            
            // Check different possible data formats
            if (data.agent_id && data.status) {
                console.log('Found standard format with agent_id and status');
                updateWorkflowVisualization(data);
            } else if (data.data && data.data.agent_id) {
                console.log('Found nested data format');
                updateWorkflowVisualization(data.data);
            } else if (data.agent && data.state) {
                console.log('Found alternative format with agent and state');
                updateWorkflowVisualization({
                    agent_id: data.agent,
                    status: data.state
                });
            } else {
                // Try to extract from any format by looking for agent and status fields
                let agentId = data.agent_id || data.agent || data.agentId;
                let status = data.status || data.state || data.statusUpdate;
                
                if (agentId && status) {
                    console.log('Found agent and status in alternative fields:', { agentId, status });
                    updateWorkflowVisualization({
                        agent_id: agentId,
                        status: status
                    });
                } else {
                    console.warn('Unrecognized status update format:', data);
                }
            }
        } catch (error) {
            console.error('Error parsing status update:', error);
            console.error('Raw event data:', event.data);
        }
    }
    
    // Handle report events
    function handleReportEvent(event) {
        console.log('Report received:', event.data);
        try {
            const data = JSON.parse(event.data);
            displayReport(data.data || data);
        } catch (error) {
            console.error('Error parsing report:', error);
        }
    }
    
    // Handle complete events
    function handleCompleteEvent(event) {
        console.log('Simulation complete:', event.data);
        try {
            // Ensure the visualization shows the final state
            // Set coordinator and any agents still in 'running' to 'complete'
            nodeStates['coordinator'] = 'complete';  // Explicitly set coordinator to complete
            Object.keys(nodeStates).forEach(key => {
                if (nodeStates[key] === 'running') {
                    console.log(`Setting agent ${key} to complete state`);
                    nodeStates[key] = 'complete';
                }
            });
            renderMermaidDiagram();
            
            // Close the EventSource since we're done
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
            
            updateConnectionStatus('complete', 'Simulation complete');
            
            // Auto-fetch report with multiple attempts
            // Given backend issues, we'll try multiple times with increasing delays
            console.log("Starting auto-fetch sequence for report");
            
            let fetchAttempt = 0;
            const maxFetchAttempts = 3;
            
            function attemptFetch() {
                fetchAttempt++;
                console.log(`Auto-fetch attempt ${fetchAttempt}/${maxFetchAttempts}`);
                
                // Attempt to fetch the report
                fetchReportDirectly(false); // Pass false to not show loading indicator on each try
                
                // If we haven't received a report and haven't reached max attempts, try again
                if (!reportReceived && fetchAttempt < maxFetchAttempts) {
                    const delay = 1000 * fetchAttempt;
                    console.log(`Will try again in ${delay}ms`);
                    setTimeout(attemptFetch, delay);
                } else if (!reportReceived) {
                    console.log("Auto-fetch sequence completed without success");
                    // Show a message that user may need to fetch manually
                    markdownSummary.innerHTML = `
                        <div class="notice">
                            <h3>Simulation Complete</h3>
                            <p>The simulation has finished, but the report could not be fetched automatically.</p>
                            <p>Please click the "Fetch Report" button to retrieve the results.</p>
                        </div>
                    `;
                }
            }
            
            // Start the first attempt after a short delay
            setTimeout(attemptFetch, 500);
            
            // Re-enable the run button
            runSimulation.disabled = false;
            runSimulation.innerHTML = '<i class="fas fa-play-circle"></i> Run Simulation';
            
        } catch (error) {
            console.error('Error handling complete event:', error);
        }
    }

    // Handle SSE connection errors
    function handleSSEError(event, runId) {
        console.error('SSE Error:', event);
        
        if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            const currentDelay = reconnectDelay * Math.pow(2, reconnectAttempts - 1);
            console.log(`Reconnecting in ${currentDelay}ms (attempt ${reconnectAttempts}/${maxReconnectAttempts})...`);
            
            updateConnectionStatus('connecting', `Reconnecting (${reconnectAttempts}/${maxReconnectAttempts})...`);
            
            setTimeout(() => {
                if (eventSource) {
                    eventSource.close();
                    eventSource = null;
                }
                connectSSE(runId);
            }, currentDelay);
        } else {
            console.error('Max reconnect attempts reached. Giving up.');
            updateConnectionStatus('error', 'Connection lost');
            
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
            
            // Re-enable the run button
            runSimulation.disabled = false;
            runSimulation.innerHTML = '<i class="fas fa-play-circle"></i> Run Simulation';
        }
    }

    // Update connection status indicator
    function updateConnectionStatus(state, message = '') {
        if (!statusIndicator || !statusText) return;
        
        statusIndicator.className = 'status-indicator';
        statusIndicator.classList.add(state);
        statusText.textContent = message;
    }

    // Show flash message
    function showMessage(message, type = 'info') {
        console.log(`Message (${type}):`, message);
        // You could implement a toast/flash message system here
        // For now, just log to console
    }

    // Initialize visualization with all agents inactive
    function initializeVisualization() {
        // Set all nodes to inactive
        Object.keys(agentMap).forEach(key => {
            nodeStates[key] = 'inactive';
        });
        
        // Render the initial diagram
        setTimeout(() => {
            renderMermaidDiagram();
        }, 100);
    }
    
    // Reset visualization for a new run
    function resetVisualization() {
        // Set all nodes to inactive
        Object.keys(agentMap).forEach(key => {
            nodeStates[key] = 'inactive';
        });
        
        // Set coordinator to running
        nodeStates['coordinator'] = 'running';
        
        // Re-render the diagram
        renderMermaidDiagram();
    }

    // Update agent key normalization
    function normalizeAgentKey(agentId) {
        // Handle empty or null input
        if (!agentId) {
            console.warn('Empty or null agent ID provided');
            return '';
        }

        // Convert to string, lowercase, and trim whitespace
        let normalized = String(agentId).toLowerCase().trim();

        // Special case for Coordinator
        if (normalized === 'coordinator') {
            return 'coordinator';
        }

        // Remove 'agent' suffix if present (case-insensitive)
        normalized = normalized.replace(/agent$/i, '');

        // Replace non-alphanumeric characters (except underscores) with underscores
        normalized = normalized.replace(/[^a-z0-9_]+/g, '_');

        // Remove multiple consecutive underscores
        normalized = normalized.replace(/_+/g, '_');

        // Remove leading and trailing underscores
        normalized = normalized.replace(/^_+|_+$/g, '');

        // Add '_agent' suffix if not already present and not coordinator
        if (!normalized.endsWith('_agent')) {
            normalized = normalized + '_agent';
        }

        return normalized;
    }

    // Update workflow visualization based on status data
    function updateWorkflowVisualization(statusData) {
        console.log('Updating workflow visualization with data:', statusData);
        
        // Skip if we don't have agent data
        if (!statusData || !statusData.agent_id) {
            console.warn('Invalid status data:', statusData);
            return;
        }
        
        // Normalize agent_id using the new function
        let agentKey = normalizeAgentKey(statusData.agent_id);
        console.log('Normalized agent key:', agentKey);
        
        // Get status from the data
        const status = statusData.status ? statusData.status.toLowerCase() : '';
        console.log('Normalized status:', status);
        
        // Update agent state
        updateAgentState(agentKey, status, statusData.message || '');
    }

    // Update agent state and re-render diagram if needed
    function updateAgentState(agentKey, status, message = '') {
        console.log('Updating agent state:', { agentKey, status, message });
        
        // Skip if unknown agent
        if (!agentMap[agentKey]) {
            console.warn(`Unknown agent: ${agentKey}`);
            return;
        }
        
        // Map status to state
        let newState;
        switch (status) {
            case 'active':
            case 'running':
            case 'start':
            case 'processing':
                newState = 'running';
                break;
            case 'done':
            case 'complete':
            case 'completed':
            case 'success':
                newState = 'complete';
                break;
            case 'error':
            case 'failed':
            case 'failure':
                newState = 'error';
                break;
            default:
                newState = 'inactive';
        }
        
        console.log('Mapped status to state:', { status, newState });
        
        // Only update and re-render if state changed
        if (newState !== nodeStates[agentKey]) {
            console.log(`Agent ${agentKey} changed state: ${nodeStates[agentKey]} -> ${newState}`);
            nodeStates[agentKey] = newState;
            console.log('Current node states:', nodeStates);
            renderMermaidDiagram();
        } else {
            console.log(`No state change needed for ${agentKey} (current: ${nodeStates[agentKey]})`);
        }
    }

    // Render Mermaid diagram based on current node states
    async function renderMermaidDiagram() {
        const diagramContainer = document.getElementById('workflowDiagram');
        if (!diagramContainer) return;
        
        const svgId = 'mermaid-workflow-svg';
        
        // Build the diagram definition with proper newlines
        let definition = [];
        
        // Start with flowchart declaration and direction
        definition.push('flowchart LR');
        
        // Add style statements for each state
        definition.push('classDef running fill:#3B82F6,stroke:#2563EB,color:#FFFFFF,stroke-width:2px');
        definition.push('classDef complete fill:#10B981,stroke:#059669,color:#FFFFFF,stroke-width:1px');
        definition.push('classDef error fill:#EF4444,stroke:#DC2626,color:#FFFFFF,stroke-width:1px');
        definition.push('classDef inactive fill:#F3F4F6,stroke:#E5E7EB,color:#4B5563,stroke-width:1px');
        
        // Define nodes with their classes
        Object.keys(agentMap).forEach(key => {
            const agent = agentMap[key];
            const state = nodeStates[key] || 'inactive';
            definition.push(`${agent.id}["${agent.name}"]:::${state}`);
        });
        
        // Add edges - now including Summary Agent
        definition.push(`${agentMap.coordinator.id} --> ${agentMap.ehr_agent.id}`);
        definition.push(`${agentMap.coordinator.id} --> ${agentMap.imaging_agent.id}`);
        definition.push(`${agentMap.coordinator.id} --> ${agentMap.pathology_agent.id}`);
        definition.push(`${agentMap.coordinator.id} --> ${agentMap.guideline_agent.id}`);
        definition.push(`${agentMap.coordinator.id} --> ${agentMap.specialist_agent.id}`);
        definition.push(`${agentMap.coordinator.id} --> ${agentMap.evaluation_agent.id}`);
        
        // Add Summary Agent connections - it receives input from all other agents except coordinator
        definition.push(`${agentMap.ehr_agent.id} --> ${agentMap.summary_agent.id}`);
        definition.push(`${agentMap.imaging_agent.id} --> ${agentMap.summary_agent.id}`);
        definition.push(`${agentMap.pathology_agent.id} --> ${agentMap.summary_agent.id}`);
        definition.push(`${agentMap.guideline_agent.id} --> ${agentMap.summary_agent.id}`);
        definition.push(`${agentMap.specialist_agent.id} --> ${agentMap.summary_agent.id}`);
        definition.push(`${agentMap.evaluation_agent.id} --> ${agentMap.summary_agent.id}`);
        
        // Join all lines with newlines
        const finalDefinition = definition.join('\n');
        
        console.log('Mermaid definition:', finalDefinition);
        
        try {
            diagramContainer.innerHTML = '<div class="loading">Rendering diagram...</div>';
            const { svg } = await mermaid.render(svgId, finalDefinition);
            diagramContainer.innerHTML = svg;
            
            // Add specific styles to the SVG element after rendering
            const svgElement = diagramContainer.querySelector('svg');
            if (svgElement) {
                svgElement.style.width = '100%';
                svgElement.style.height = 'auto';
                svgElement.style.minHeight = '300px';
            }
            
            console.log('Node states:', nodeStates);
        } catch (error) {
            console.error('Failed to render Mermaid diagram:', error);
            diagramContainer.innerHTML = `
                <details class="error-details">
                    <summary>Error rendering diagram</summary>
                    <p>${error.message || 'Unknown error'}</p>
                    <pre>${finalDefinition}</pre>
                </details>
            `;
        }
    }

    // Display report in the UI
    function displayReport(data) {
        console.log('Displaying report data:', data);
        
        // Set global flag that we've received a report
        reportReceived = true;
        
        try {
            // Check if we need to look inside mdtReport structure
            const reportData = data.mdtReport || data;
            
            // Extract patient ID if present
            const patientId = reportData.patient_id || "Unknown Patient";
            const patientIdElement = document.getElementById('patient-id');
            if (patientIdElement) {
                patientIdElement.textContent = patientId;
            }
            
            // Display the summary in the markdown view
            const markdownSummary = document.getElementById('markdownSummary');
            
            // Get the markdown content using our helper function
            const markdownContent = getMarkdownContent(reportData);
            
            if (markdownContent) {
                console.log("Found markdown content to display");
                
                // Check if the content is already in HTML format
                if (markdownContent.startsWith('<') && markdownContent.includes('</')) {
                    markdownSummary.innerHTML = markdownContent;
                } else {
                    markdownSummary.innerHTML = renderMarkdown(markdownContent);
                }
            } else {
                // If no suitable content found, create a basic summary
                console.log("No suitable markdown content found, creating basic summary");
                markdownSummary.innerHTML = renderMarkdown(`# Report for ${patientId}\n\nNo summary available.`);
            }
            
            // Create the agent detail sections
            createAgentDetailSections(reportData);
            
            // Scroll to the report section if it exists
            const reportSection = document.getElementById('report-section');
            if (reportSection) {
                reportSection.scrollIntoView({ behavior: 'smooth' });
            }
            
            // Update the current report data for copying
            currentReportData = reportData;
            
            // Show the report container and hide loading indicators
            document.querySelector('.report-container').style.display = 'flex';
            
            return true;
        } catch (error) {
            console.error('Error displaying report:', error);
            markdownSummary.innerHTML = `
                <div class="error">
                    <h3>Error Displaying Report</h3>
                    <p>An error occurred while trying to display the report: ${error.message}</p>
                    <p>Please try again or contact support if the problem persists.</p>
                </div>
            `;
            return false;
        }
    }
    
    // Create collapsible detail sections for each agent
    function createAgentDetailSections(data) {
        agentOutputs.innerHTML = '';
        
        // Check if we need to look inside mdtReport structure
        const reportData = data.mdtReport || data;
        
        // Special handling for SummaryAgent output - ensure it's displayed in the markdown section
        if (reportData.summary_agent || reportData.summaryAgent) {
            const summaryAgentData = reportData.summary_agent || reportData.summaryAgent;
            // Extract content and ensure it's displayed in the markdown view
            if (summaryAgentData && typeof summaryAgentData === 'object') {
                const content = summaryAgentData.output || summaryAgentData.content || summaryAgentData.text || summaryAgentData.markdown;
                if (content && typeof content === 'string') {
                    // Update the markdown view with this content
                    const markdownView = document.getElementById('markdownSummary');
                    markdownView.innerHTML = renderMarkdown(content);
                    console.log("Updated markdown view with SummaryAgent content");
                }
            }
        }
        
        // Map of expected agent keys in the report data
        const agentDataMapping = {
            'ehrReport': { key: 'ehr_agent', title: 'EHR Report' },
            'imagingReport': { key: 'imaging_agent', title: 'Imaging Report' },
            'pathologyReport': { key: 'pathology_agent', title: 'Pathology Report' },
            'guidelineReport': { key: 'guideline_agent', title: 'Guideline Report' },
            'specialistReport': { key: 'specialist_agent', title: 'Specialist Report' },
            'evaluationReport': { key: 'evaluation_agent', title: 'Evaluation Report' }
        };
        
        // Alternative keys that might be used
        const alternativeKeys = {
            'ehr_analysis': 'ehrReport',
            'imaging_analysis': 'imagingReport',
            'pathology_analysis': 'pathologyReport',
            'guideline_recommendations': 'guidelineReport',
            'specialist_assessment': 'specialistReport',
            'evaluation': 'evaluationReport',
            'evaluation_score': 'evaluationReport',
            'evaluation_comments': 'evaluationReport',
            'evaluation_formatted': 'evaluationReport'
        };
        
        // Track which agent sections we've already created
        const createdSections = new Set();
        
        // Check for the presence of any report data and create sections
        let hasCreatedAnySection = false;
        
        // First try with the standard keys
        Object.keys(agentDataMapping).forEach(dataKey => {
            const agentInfo = agentDataMapping[dataKey];
            if (!createdSections.has(agentInfo.key) && reportData[dataKey]) {
                createSectionWithData(reportData[dataKey], agentInfo);
                createdSections.add(agentInfo.key);
                hasCreatedAnySection = true;
            }
        });
        
        // If some sections still need to be created, try with alternative keys
        Object.keys(alternativeKeys).forEach(altKey => {
            const mappedKey = alternativeKeys[altKey];
            const agentInfo = agentDataMapping[mappedKey];
            
            // Skip if we already created this section
            if (createdSections.has(agentInfo.key)) return;
            
            // Check if this alternative key has data
            if (reportData[altKey]) {
                // Special case for evaluation fields that need to be combined
                if (mappedKey === 'evaluationReport' && 
                   (altKey === 'evaluation_score' || altKey === 'evaluation_comments' || altKey === 'evaluation_formatted')) {
                    // Only create evaluation section if we haven't already
                    if (!createdSections.has('evaluation_agent')) {
                        // Create combined evaluation data
                        const evaluationData = {
                            score: reportData.evaluation_score,
                            comments: reportData.evaluation_comments || 'No comments provided',
                            formatted: reportData.evaluation_formatted || '',
                            evaluation: reportData.evaluation || {}
                        };
                        
                        createSectionWithData(evaluationData, agentInfo);
                        createdSections.add(agentInfo.key);
                        hasCreatedAnySection = true;
                    }
                } else {
                    // Regular alternative key handling
                    createSectionWithData(reportData[altKey], agentInfo);
                    createdSections.add(agentInfo.key);
                    hasCreatedAnySection = true;
                }
            }
        });
        
        // If we still don't have any sections, look for any agent-related keys
        if (!hasCreatedAnySection) {
            // Look for any keys that might contain agent data
            Object.keys(reportData).forEach(key => {
                let mappedAgent = null;
                
                // Check if the key contains any agent name
                Object.keys(agentMap).forEach(agentKey => {
                    // Skip if we already created this section
                    if (createdSections.has(agentKey)) return;
                    
                    const agentName = agentKey.replace('_agent', '');
                    if (key.toLowerCase().includes(agentName)) {
                        // Found a potential match
                        mappedAgent = {
                            key: agentKey,
                            title: agentMap[agentKey].name
                        };
                    }
                });
                
                if (mappedAgent && !createdSections.has(mappedAgent.key)) {
                    createSectionWithData(reportData[key], mappedAgent);
                    createdSections.add(mappedAgent.key);
                    hasCreatedAnySection = true;
                }
            });
        }
        
        // Helper function to create a section with given data
        function createSectionWithData(agentData, agentInfo) {
            // Get agent info from map
            const agentMapInfo = agentMap[agentInfo.key] || { icon: 'fa-file-medical' };
            
            // Create details element
            const details = document.createElement('details');
            details.className = 'agent-details';
            
            // Create summary (the clickable header)
            const summary = document.createElement('summary');
            summary.innerHTML = `
                <div class="agent-icon">
                    <i class="fas ${agentMapInfo.icon}"></i>
                </div>
                ${agentInfo.title}
            `;
            
            // Create content container
            const content = document.createElement('div');
            content.className = 'agent-content';
            
            // Convert to markdown
            let markdown = '';
            
            if (typeof agentData === 'string') {
                markdown = agentData;
            } else if (typeof agentData === 'object') {
                if (Array.isArray(agentData)) {
                    // Handle array data
                    markdown = `# ${agentInfo.title}\n\n`;
                    agentData.forEach((item, index) => {
                        markdown += `## Item ${index + 1}\n\n`;
                        if (typeof item === 'object') {
                            Object.keys(item).forEach(key => {
                                markdown += `### ${formatTitle(key)}\n\n${formatValue(item[key])}\n\n`;
                            });
                        } else {
                            markdown += `${item}\n\n`;
                        }
                    });
                } else {
                    // Handle object data
                    markdown = objectToMarkdown(agentData, agentInfo.title);
                }
            }
            
            // Apply markdown conversion
            content.innerHTML = renderMarkdown(markdown);
            
            // Add to the details element
            details.appendChild(summary);
            details.appendChild(content);
            
            // Add to the page
            agentOutputs.appendChild(details);
        }
    }
    
    // Generate a basic summary from the report data structure
    function generateSummaryFromReport(data) {
        let summary = '# MDT Summary Report\n\n';
        
        // Try to extract data from different possible structures
        const reportData = data.mdtReport || data;
        
        // Add patient info if available
        if (reportData.patientInfo || reportData.patient_info || reportData.patient) {
            const patientInfo = reportData.patientInfo || reportData.patient_info || reportData.patient || {};
            summary += '## Patient Information\n\n';
            
            // Try different possible field names
            const name = patientInfo.name || patientInfo.patient_name || '';
            const age = patientInfo.age || '';
            const gender = patientInfo.gender || patientInfo.sex || '';
            const diagnosis = patientInfo.diagnosis || patientInfo.primary_diagnosis || '';
            
            if (name) summary += `**Name:** ${name}\n\n`;
            if (age) summary += `**Age:** ${age}\n\n`;
            if (gender) summary += `**Gender:** ${gender}\n\n`;
            if (diagnosis) summary += `**Diagnosis:** ${diagnosis}\n\n`;
        }
        
        // Add conclusion if available
        const conclusion = reportData.conclusion || reportData.final_conclusion || reportData.summary || '';
        if (conclusion) {
            summary += '## Conclusion\n\n';
            summary += conclusion + '\n\n';
        }
        
        // Add recommendations if available
        const recommendations = reportData.recommendations || reportData.treatment_recommendations || [];
        if (recommendations && (Array.isArray(recommendations) ? recommendations.length > 0 : recommendations)) {
            summary += '## Recommendations\n\n';
            
            if (Array.isArray(recommendations)) {
                recommendations.forEach(rec => {
                    summary += `- ${rec}\n`;
                });
            } else if (typeof recommendations === 'string') {
                summary += recommendations;
            } else if (typeof recommendations === 'object') {
                Object.keys(recommendations).forEach(key => {
                    summary += `### ${formatTitle(key)}\n\n`;
                    const value = recommendations[key];
                    if (Array.isArray(value)) {
                        value.forEach(item => {
                            summary += `- ${item}\n`;
                        });
                    } else {
                        summary += `${value}\n\n`;
                    }
                });
            }
        }
        
        // If we couldn't extract specific fields, use general data
        if (summary === '# MDT Summary Report\n\n') {
            Object.keys(reportData).forEach(key => {
                // Skip keys that are likely to be agent reports
                if (key.includes('Report') || key.includes('Analysis') || key.includes('assessment')) {
                    return;
                }
                
                const value = reportData[key];
                if (value && typeof value !== 'object') {
                    summary += `## ${formatTitle(key)}\n\n${value}\n\n`;
                }
            });
        }
        
        return summary;
    }
    
    // Convert an object to markdown
    function objectToMarkdown(obj, title) {
        let markdown = `# ${title}\n\n`;
        
        // Process each key
        Object.keys(obj).forEach(key => {
            const value = obj[key];
            
            // Format key as heading
            const heading = formatTitle(key);
            markdown += `## ${heading}\n\n`;
            
            // Format value based on type
            markdown += formatValue(value);
            markdown += '\n\n';
        });
        
        return markdown;
    }
    
    // Format a key into a title
    function formatTitle(str) {
        return str
            .replace(/([A-Z])/g, ' $1')
            .replace(/^./, match => match.toUpperCase())
            .replace(/_/g, ' ')
            .trim();
    }
    
    // Format a value based on its type
    function formatValue(value) {
        if (value === null || value === undefined) {
            return 'N/A';
        }
        
        if (Array.isArray(value)) {
            if (value.length === 0) return 'None';
            
            if (typeof value[0] === 'object') {
                // Array of objects - build a table
                return buildMarkdownTable(value);
            }
            
            // Simple array - build a list
            return value.map(item => `- ${item}`).join('\n');
        }
        
        if (typeof value === 'object') {
            return objectToNestedMarkdown(value);
        }
        
        return value.toString();
    }
    
    // Convert an object to nested markdown
    function objectToNestedMarkdown(obj) {
        let markdown = '';
        
        Object.keys(obj).forEach(key => {
            const value = obj[key];
            const heading = formatTitle(key);
            
            markdown += `### ${heading}\n\n`;
            
            if (value === null || value === undefined) {
                markdown += 'N/A\n\n';
            } else if (Array.isArray(value)) {
                if (value.length === 0) {
                    markdown += 'None\n\n';
                } else if (typeof value[0] === 'object') {
                    markdown += buildMarkdownTable(value) + '\n\n';
                } else {
                    markdown += value.map(item => `- ${item}`).join('\n') + '\n\n';
                }
            } else if (typeof value === 'object') {
                Object.keys(value).forEach(subKey => {
                    const subValue = value[subKey];
                    const subHeading = formatTitle(subKey);
                    
                    markdown += `#### ${subHeading}\n\n`;
                    markdown += (subValue || 'N/A').toString() + '\n\n';
                });
            } else {
                markdown += value.toString() + '\n\n';
            }
        });
        
        return markdown;
    }
    
    // Build a markdown table from an array of objects
    function buildMarkdownTable(array) {
        if (!array || array.length === 0) return 'No data available';
        
        // Get headers from the first object
        const headers = Object.keys(array[0]);
        if (headers.length === 0) return 'Empty data';
        
        // Build header row
        let table = '| ' + headers.join(' | ') + ' |\n';
        table += '| ' + headers.map(() => '---').join(' | ') + ' |\n';
        
        // Build data rows
        array.forEach(obj => {
            const row = headers.map(header => obj[header] || 'N/A');
            table += '| ' + row.join(' | ') + ' |\n';
        });
        
        return table;
    }

    // Fetch report manually
    async function fetchReportManually() {
        const runId = runIdInput.value.trim();
        if (!runId) {
            alert('Please enter a Run ID');
            return;
        }
        
        try {
            // Show loading indicator
            markdownSummary.innerHTML = '<div class="loading">Fetching report...</div>';
            agentOutputs.innerHTML = '';
            
            // Try up to 3 times with a delay
            let reportData = null;
            let attempts = 0;
            const maxAttempts = 3;
            
            while (attempts < maxAttempts && !reportData) {
                try {
                    attempts++;
                    
                    // Try the primary endpoint
                    const response = await fetch(`${apiBase}/report/${runId}`);
                    
                    if (response.ok) {
                        reportData = await response.json();
                        console.log("Report fetched manually:", reportData);
                        break;
                    } else {
                        console.warn(`Attempt ${attempts}/${maxAttempts} failed. Status: ${response.status}`);
                        
                        if (attempts < maxAttempts) {
                            // Wait longer between each attempt
                            const delay = 1000 * attempts;
                            console.log(`Waiting ${delay}ms before retry...`);
                            await new Promise(resolve => setTimeout(resolve, delay));
                        }
                    }
                } catch (error) {
                    console.error(`Fetch attempt ${attempts} error:`, error);
                    
                    if (attempts < maxAttempts) {
                        // Wait longer between each attempt
                        const delay = 1000 * attempts;
                        console.log(`Waiting ${delay}ms before retry...`);
                        await new Promise(resolve => setTimeout(resolve, delay));
                    }
                }
            }
            
            // If we didn't get data from the primary endpoint, try the fallback
            if (!reportData) {
                console.log("Trying fallback report endpoint...");
                try {
                    const response = await fetch(`${apiBase}/latest-report/${runId}`);
                    if (response.ok) {
                        reportData = await response.json();
                        console.log("Report fetched from fallback endpoint:", reportData);
                    }
                } catch (fallbackError) {
                    console.error("Fallback report endpoint failed:", fallbackError);
                }
            }
            
            // If we have report data, display it
            if (reportData) {
                displayReport(reportData);
            } else {
                markdownSummary.innerHTML = `
                    <div class="error">
                        <h3>Error: Unable to fetch report</h3>
                        <p>We couldn't retrieve the report for run ID: ${runId}</p>
                        <p>The report might not exist or there could be a server error.</p>
                    </div>
                `;
                agentOutputs.innerHTML = '';
            }
            
        } catch (error) {
            console.error('Error fetching report manually:', error);
            markdownSummary.innerHTML = `
                <div class="error">
                    <h3>Error: ${error.message}</h3>
                    <p>Please check that the Run ID is correct and try again.</p>
                </div>
            `;
            agentOutputs.innerHTML = '';
        }
    }

    // Fetch report directly (used when simulation completes)
    async function fetchReportDirectly(showLoading = true) {
        if (!currentRunId) {
            console.log('No run ID available for direct report fetch');
            return;
        }
        
        try {
            // Show loading indicator if requested
            if (showLoading) {
                markdownSummary.innerHTML = '<div class="loading">Fetching report...</div>';
            }
            
            // First try the /report/{runId} endpoint
            console.log(`Attempting to fetch report for run ID: ${currentRunId}`);
            
            // Try up to 3 times with a delay
            let reportData = null;
            let attempts = 0;
            const maxAttempts = 3;
            
            while (attempts < maxAttempts && !reportData) {
                try {
                    attempts++;
                    
                    // Try the primary endpoint
                    const response = await fetch(`${apiBase}/report/${currentRunId}`);
                    
                    if (response.ok) {
                        reportData = await response.json();
                        console.log("Report fetched successfully:", reportData);
                        
                        // Debug: Check for markdown_summary field
                        if (reportData.markdown_summary) {
                            console.log("DEBUG: markdown_summary field found:", reportData.markdown_summary.substring(0, 100) + "...");
                        } else {
                            console.log("DEBUG: No markdown_summary field found in report data");
                        }
                        
                        break;
                    } else {
                        console.warn(`Attempt ${attempts}/${maxAttempts} failed. Status: ${response.status}`);
                        
                        if (attempts < maxAttempts) {
                            // Wait longer between each attempt
                            const delay = 1000 * attempts;
                            console.log(`Waiting ${delay}ms before retry...`);
                            await new Promise(resolve => setTimeout(resolve, delay));
                        }
                    }
                } catch (error) {
                    console.error(`Fetch attempt ${attempts} error:`, error);
                    
                    if (attempts < maxAttempts) {
                        // Wait longer between each attempt
                        const delay = 1000 * attempts;
                        console.log(`Waiting ${delay}ms before retry...`);
                        await new Promise(resolve => setTimeout(resolve, delay));
                    }
                }
            }
            
            // If we didn't get data from the primary endpoint, try the fallback
            if (!reportData) {
                console.log("Trying fallback report endpoint...");
                try {
                    const response = await fetch(`${apiBase}/latest-report/${currentRunId}`);
                    if (response.ok) {
                        reportData = await response.json();
                        console.log("Report fetched from fallback endpoint:", reportData);
                        
                        // Debug: Check for markdown_summary field
                        if (reportData.markdown_summary) {
                            console.log("DEBUG: markdown_summary field found in fallback data:", reportData.markdown_summary.substring(0, 100) + "...");
                        } else {
                            console.log("DEBUG: No markdown_summary field found in fallback data");
                        }
                    }
                } catch (fallbackError) {
                    console.error("Fallback report endpoint failed:", fallbackError);
                }
            }
            
            // If we have report data, display it
            if (reportData) {
                displayReport(reportData);
                return true; // Report was successfully fetched and displayed
            } else {
                // Only show error if we're explicitly showing loading
                if (showLoading) {
                    // Create a basic report from the status updates we've seen
                    console.log("Creating synthetic report from status updates");
                    const syntheticReport = createSyntheticReport();
                    displayReport(syntheticReport);
                }
                return false; // Report could not be fetched
            }
            
        } catch (error) {
            console.error('Error fetching report directly:', error);
            if (showLoading) {
                markdownSummary.innerHTML = `
                    <div class="error">
                        <p>Error fetching report: ${error.message}</p>
                        <p>You can try manually fetching the report using the Run ID.</p>
                    </div>
                `;
            }
            return false; // Report could not be fetched
        }
    }

    // Create a synthetic report from status updates we've seen
    function createSyntheticReport() {
        // Basic report structure
        const report = {
            patient_id: currentRunId,
            summary: "# MDT Simulation Summary\n\nThe simulation completed, but we couldn't retrieve the full report data from the server. This is a simplified summary based on the workflow status.",
            timestamp: new Date().toISOString()
        };
        
        // Add information about which agents completed
        let agentStatuses = '';
        Object.keys(nodeStates).forEach(key => {
            const state = nodeStates[key];
            const name = agentMap[key] ? agentMap[key].name : key;
            const statusEmoji = state === 'complete' ? '✅' : state === 'error' ? '❌' : state === 'running' ? '⏳' : '⏹️';
            agentStatuses += `- ${statusEmoji} **${name}**: ${state}\n`;
        });
        
        report.summary += "\n\n## Agent Statuses\n\n" + agentStatuses;
        
        // Add recommendation to fetch report manually
        report.summary += "\n\n## Recommendations\n\n" +
            "- Try fetching the report manually with the Run ID\n" +
            "- Check the server logs for more information about any errors\n" +
            "- If the issue persists, contact system support";
        
        return report;
    }

    // Basic markdown parser fallback in case marked.js is not loaded
    function basicMarkdownToHtml(markdown) {
        if (!markdown) return '';
        
        // Replace headers
        let html = markdown
            .replace(/^# (.*$)/gm, '<h1>$1</h1>')
            .replace(/^## (.*$)/gm, '<h2>$1</h2>')
            .replace(/^### (.*$)/gm, '<h3>$1</h3>')
            .replace(/^#### (.*$)/gm, '<h4>$1</h4>');
            
        // Replace bold and italic
        html = html
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
            
        // Replace lists
        html = html
            .replace(/^\s*- (.*$)/gm, '<li>$1</li>')
            .replace(/(<li>.*<\/li>\n)+/g, '<ul>$&</ul>');
            
        // Replace paragraphs
        html = html
            .replace(/^(?!<h|<ul|<li|<\/)(.*$)/gm, function(match) {
                return match.trim() ? '<p>' + match + '</p>' : '';
            });
            
        return html;
    }

    // Safe markdown rendering function
    function renderMarkdown(markdown) {
        if (!markdown) return '';
        
        try {
            // Try to use marked.js if available
            if (typeof marked !== 'undefined') {
                return marked.parse(markdown);
            } else {
                // Fallback to basic parser
                console.warn('marked.js not available, using basic markdown parser');
                return basicMarkdownToHtml(markdown);
            }
        } catch (error) {
            console.error('Error parsing markdown:', error);
            // Return escaped text as fallback
            return markdown
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/\n/g, '<br>');
        }
    }

    // Helper function to ensure markdown is properly extracted 
    function getMarkdownContent(data) {
        // Try to get content from multiple possible locations
        if (data.markdown_summary) {
            return data.markdown_summary;
        } 
        
        // Look for summary agent output in specific fields
        if (data.summary_agent && data.summary_agent.output) {
            return data.summary_agent.output;
        }
        
        // Check if there's a SummaryAgent section in the data
        for (const key in data) {
            if (key.toLowerCase().includes('summary') && typeof data[key] === 'object') {
                if (data[key].markdown || data[key].text || data[key].content) {
                    return data[key].markdown || data[key].text || data[key].content;
                }
            }
        }
        
        // Fall back to regular summary if nothing else is found
        if (data.summary && typeof data.summary === 'string') {
            return data.summary;
        }
        
        return null;
    }
});
