// Google Meet Attendance & Engagement Dashboard
let attendanceData = null;

// Load data when page loads
document.addEventListener('DOMContentLoaded', async function() {
    try {
        const response = await fetch('attendance_report.json');
        attendanceData = await response.json();
        initializeDashboard();
    } catch (error) {
        console.error('Error loading data:', error);
        document.querySelector('.container').innerHTML = `
            <div style="text-align: center; padding: 50px;">
                <h2>Error Loading Data</h2>
                <p>Could not load attendance_report.json. Please ensure the file exists and the Python script has been run.</p>
                <button onclick="location.reload()">Retry</button>
            </div>
        `;
    }
});

function initializeDashboard() {
    if (!attendanceData) return;
    
    updateSummaryCards();
    populateSessionSelect();
    createCharts();
    updateStudentLists();
}

function updateSummaryCards() {
    const summary = attendanceData.summary;
    
    document.getElementById('total-sessions').textContent = summary.total_sessions;
    document.getElementById('unique-students').textContent = summary.total_unique_students;
    document.getElementById('avg-attendance').textContent = summary.avg_attendance_per_session;
    document.getElementById('teacher-name').textContent = attendanceData.teacher_name;
    document.getElementById('analysis-period').textContent = 
        `Analysis Period: ${summary.date_range.start} to ${summary.date_range.end}`;
}

function populateSessionSelect() {
    const select = document.getElementById('sessionSelect');
    const sessions = attendanceData.sessions;
    
    // Clear existing options except the first one
    select.innerHTML = '<option value="">Select a session...</option>';
    
    // Add sessions sorted by date
    Object.keys(sessions)
        .sort((a, b) => new Date(a) - new Date(b))
        .forEach(date => {
            const session = sessions[date];
            const option = document.createElement('option');
            option.value = date;
            option.textContent = `${date} - ${session.time} (${session.total_attendees} attendees)`;
            select.appendChild(option);
        });
    
    // Add event listener
    select.addEventListener('change', function() {
        if (this.value) {
            displaySessionData(this.value);
        } else {
            document.getElementById('sessionData').innerHTML = '';
        }
    });
}

function displaySessionData(sessionDate) {
    const session = attendanceData.sessions[sessionDate];
    const container = document.getElementById('sessionData');
    
    const html = `
        <div class="session-info">
            <div class="info-card">
                <h4>Date</h4>
                <p>${session.date}</p>
            </div>
            <div class="info-card">
                <h4>Time</h4>
                <p>${session.time}</p>
            </div>
            <div class="info-card">
                <h4>Attendees</h4>
                <p>${session.total_attendees}</p>
            </div>
            <div class="info-card">
                <h4>Speakers</h4>
                <p>${session.total_speakers}</p>
            </div>
            <div class="info-card">
                <h4>Chatters</h4>
                <p>${session.total_chatters}</p>
            </div>
            <div class="info-card">
                <h4>Silent Students</h4>
                <p>${session.silent_students.length}</p>
            </div>
        </div>
        
        <div class="session-details">
            <div class="detail-section">
                <h4>Speaking Interactions (${session.total_speakers} students)</h4>
                <div class="speaker-list">
                    ${Object.entries(session.speaking_interactions)
                        .sort((a, b) => b[1] - a[1])
                        .map(([name, count]) => `
                            <div class="speaker-item">
                                <strong>${name}</strong><br>
                                ${count} interaction${count !== 1 ? 's' : ''}
                            </div>
                        `).join('')}
                </div>
            </div>
            
            <div class="detail-section">
                <h4>Chat Messages (${session.total_chatters} students)</h4>
                <div class="chat-list">
                    ${Object.entries(session.chat_interactions)
                        .sort((a, b) => b[1] - a[1])
                        .map(([name, count]) => `
                            <div class="chat-item">
                                <strong>${name}</strong><br>
                                ${count} message${count !== 1 ? 's' : ''}
                            </div>
                        `).join('')}
                </div>
            </div>
            
            <div class="detail-section">
                <h4>Silent Students (${session.silent_students.length} students)</h4>
                <div class="silent-list">
                    ${session.silent_students.map(name => `
                        <div class="silent-item">
                            <strong>${name}</strong><br>
                            No interactions
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

function createCharts() {
    createEngagementChart();
    createAttendanceChart();
    createParticipationChart();
    createSessionBreakdownChart();
}

function createEngagementChart() {
    const ctx = document.getElementById('engagementChart').getContext('2d');
    const engagementMetrics = attendanceData.engagement_metrics;
    
    // Get top 10 most engaged students
    const topEngaged = Object.entries(engagementMetrics)
        .sort((a, b) => b[1].engagement_score - a[1].engagement_score)
        .slice(0, 10);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: topEngaged.map(([name]) => name.length > 15 ? name.substring(0, 15) + '...' : name),
            datasets: [{
                label: 'Engagement Score (%)',
                data: topEngaged.map(([, metrics]) => metrics.engagement_score),
                backgroundColor: 'rgba(102, 126, 234, 0.8)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        afterLabel: function(context) {
                            const metrics = topEngaged[context.dataIndex][1];
                            return [
                                `Attendance: ${metrics.attendance_rate}%`,
                                `Speaking: ${metrics.speaking_rate}%`,
                                `Chat: ${metrics.chat_rate}%`
                            ];
                        }
                    }
                }
            }
        }
    });
}

function createAttendanceChart() {
    const ctx = document.getElementById('attendanceChart').getContext('2d');
    const sessions = attendanceData.sessions;
    
    const sessionDates = Object.keys(sessions).sort((a, b) => new Date(a) - new Date(b));
    const attendanceCounts = sessionDates.map(date => sessions[date].total_attendees);
    const speakerCounts = sessionDates.map(date => sessions[date].total_speakers);
    const chatterCounts = sessionDates.map(date => sessions[date].total_chatters);
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: sessionDates.map(date => date.substring(5)), // Show MM/DD
            datasets: [
                {
                    label: 'Total Attendees',
                    data: attendanceCounts,
                    borderColor: 'rgba(102, 126, 234, 1)',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.1
                },
                {
                    label: 'Speakers',
                    data: speakerCounts,
                    borderColor: 'rgba(40, 167, 69, 1)',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    tension: 0.1
                },
                {
                    label: 'Chatters',
                    data: chatterCounts,
                    borderColor: 'rgba(255, 193, 7, 1)',
                    backgroundColor: 'rgba(255, 193, 7, 0.1)',
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function createParticipationChart() {
    const ctx = document.getElementById('participationChart').getContext('2d');
    const studentStats = attendanceData.student_overall_stats;
    
    // Prepare data for scatter plot
    const scatterData = Object.entries(studentStats).map(([name, stats]) => ({
        x: stats.total_transcript_interactions,
        y: stats.total_chat_messages,
        label: name
    }));
    
    new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Students',
                data: scatterData,
                backgroundColor: 'rgba(102, 126, 234, 0.6)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Total Speaking Interactions'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Total Chat Messages'
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return context[0].raw.label;
                        },
                        label: function(context) {
                            return [
                                `Speaking: ${context.raw.x} interactions`,
                                `Chat: ${context.raw.y} messages`
                            ];
                        }
                    }
                }
            }
        }
    });
}

function createSessionBreakdownChart() {
    const ctx = document.getElementById('sessionBreakdownChart').getContext('2d');
    const sessions = attendanceData.sessions;
    
    // Calculate averages
    const totalSessions = Object.keys(sessions).length;
    const avgAttendees = Object.values(sessions).reduce((sum, s) => sum + s.total_attendees, 0) / totalSessions;
    const avgSpeakers = Object.values(sessions).reduce((sum, s) => sum + s.total_speakers, 0) / totalSessions;
    const avgChatters = Object.values(sessions).reduce((sum, s) => sum + s.total_chatters, 0) / totalSessions;
    const avgSilent = Object.values(sessions).reduce((sum, s) => sum + s.silent_students.length, 0) / totalSessions;
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Speakers', 'Chatters', 'Silent Students'],
            datasets: [{
                data: [avgSpeakers, avgChatters, avgSilent],
                backgroundColor: [
                    'rgba(40, 167, 69, 0.8)',
                    'rgba(255, 193, 7, 0.8)',
                    'rgba(220, 53, 69, 0.8)'
                ],
                borderColor: [
                    'rgba(40, 167, 69, 1)',
                    'rgba(255, 193, 7, 1)',
                    'rgba(220, 53, 69, 1)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Average Participation Distribution'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw.toFixed(1);
                            const percentage = ((context.raw / avgAttendees) * 100).toFixed(1);
                            return `${context.label}: ${value} students (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function updateStudentLists() {
    const engagementMetrics = attendanceData.engagement_metrics;
    
    // Sort students by engagement score
    const sortedStudents = Object.entries(engagementMetrics)
        .sort((a, b) => b[1].engagement_score - a[1].engagement_score);
    
    // Top engaged students (top 10)
    const topEngaged = sortedStudents.slice(0, 10);
    const topEngagedHtml = topEngaged.map(([name, metrics]) => `
        <div class="student-item">
            <div class="student-name">${name}</div>
            <div class="student-stats">
                Engagement: ${metrics.engagement_score}% | 
                Attendance: ${metrics.attendance_rate}% | 
                Total Interactions: ${metrics.total_interactions}
            </div>
        </div>
    `).join('');
    
    // Students needing attention (bottom 10 with some attendance)
    const needingAttention = sortedStudents
        .filter(([, metrics]) => metrics.attendance_rate > 0) // Only students who attended at least once
        .slice(-10)
        .reverse(); // Show lowest engagement first
    
    const needingAttentionHtml = needingAttention.map(([name, metrics]) => {
        const engagementClass = metrics.engagement_score < 30 ? 'low-engagement' : 
                               metrics.engagement_score < 60 ? 'medium-engagement' : '';
        
        return `
            <div class="student-item ${engagementClass}">
                <div class="student-name">${name}</div>
                <div class="student-stats">
                    Engagement: ${metrics.engagement_score}% | 
                    Attendance: ${metrics.attendance_rate}% | 
                    Total Interactions: ${metrics.total_interactions}
                </div>
            </div>
        `;
    }).join('');
    
    document.getElementById('topEngagedList').innerHTML = topEngagedHtml;
    document.getElementById('lowEngagementList').innerHTML = needingAttentionHtml;
}

function exportData() {
    if (!attendanceData) {
        alert('No data available to export');
        return;
    }
    
    // Create a comprehensive CSV export
    let csvContent = "Student Name,Sessions Attended,Sessions Spoke,Sessions Chatted,Total Speaking,Total Chat,Attendance Rate,Speaking Rate,Chat Rate,Engagement Score\n";
    
    const studentStats = attendanceData.student_overall_stats;
    const engagementMetrics = attendanceData.engagement_metrics;
    
    Object.keys(studentStats).forEach(studentName => {
        const stats = studentStats[studentName];
        const metrics = engagementMetrics[studentName] || {};
        
        csvContent += [
            `"${studentName}"`,
            stats.sessions_attended || 0,
            stats.sessions_spoke || 0,
            stats.sessions_chatted || 0,
            stats.total_transcript_interactions || 0,
            stats.total_chat_messages || 0,
            metrics.attendance_rate || 0,
            metrics.speaking_rate || 0,
            metrics.chat_rate || 0,
            metrics.engagement_score || 0
        ].join(',') + '\n';
    });
    
    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'attendance_engagement_report.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    // Also offer JSON download
    const jsonBlob = new Blob([JSON.stringify(attendanceData, null, 2)], { type: 'application/json' });
    const jsonUrl = window.URL.createObjectURL(jsonBlob);
    const jsonA = document.createElement('a');
    jsonA.href = jsonUrl;
    jsonA.download = 'full_attendance_report.json';
    document.body.appendChild(jsonA);
    jsonA.click();
    document.body.removeChild(jsonA);
    window.URL.revokeObjectURL(jsonUrl);
}
