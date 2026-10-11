// data.js - Mock Data & State Management

const cineData = {
    revenue: {
        today: 124500,
        trend: 14.5,
        forecastPoints: [20, 35, 45, 60, 85, 110, 125, 150]
    },
    occupancy: 86,
    activeScreens: 24,
    ticketsSold: 8432,
    movies: [
        { id: 1, title: 'Dune: Part Two', aiScore: 98, sentiment: 'Positive' },
        { id: 2, title: 'Oppenheimer', aiScore: 92, sentiment: 'Positive' },
        { id: 3, title: 'Godzilla x Kong', aiScore: 85, sentiment: 'Mixed' }
    ],
    auditoriums: [
        { id: 1, name: 'Hall 1 (IMAX)', status: 'playing', fill: 65 },
        { id: 2, name: 'Hall 2 (4DX)', status: 'idle', fill: 0 },
        { id: 3, name: 'Hall 3 (Atmos)', status: 'alert', fill: 100 }
    ],
    users: {
        admin: { name: 'Nguyễn Văn Admin', role: 'Super Admin' },
        manager: { name: 'Trần Thị Quản Lý', role: 'Cinema Manager' },
        ai: { name: 'Lê Chuyên Viên', role: 'AI Operations Lead' }
    }
};

window.cineData = cineData;
