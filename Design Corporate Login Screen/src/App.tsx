import React, { useState, useEffect } from 'react';
import { Calendar, Lock, Mail, Eye, EyeOff, AlertCircle, LogOut, CheckCircle } from 'lucide-react';

export default function App() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userRole, setUserRole] = useState('');

  // Kiểm tra nếu đã đăng nhập trước đó
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const role = localStorage.getItem('user_role');
    if (token) {
      setIsLoggedIn(true);
      setUserRole(role || 'user');
    }
  }, []);

  // Xử lý gửi request Đăng nhập tới FastAPI Backend
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    setIsLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:8000/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (response.ok) {
        // Lưu thông tin đăng nhập
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('user_role', data.role || 'user');
        
        setUserRole(data.role || 'user');
        setIsLoggedIn(true);
      } else {
        setErrorMessage(data.detail || 'Sai tên đăng nhập hoặc mật khẩu');
      }
    } catch (err) {
      setErrorMessage('Không thể kết nối tới server Backend FastAPI (Cổng 8000)');
    } finally {
      setIsLoading(false);
    }
  };

  // Xử lý Đăng xuất
  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_role');
    setIsLoggedIn(false);
    setUsername('');
    setPassword('');
  };

  // GIỜ ĐÂY: Nếu đã Đăng nhập thành công -> Hiển thị Màn hình Dashboard Quản lý
  if (isLoggedIn) {
    return (
      <div className="min-h-screen bg-slate-50 p-8 font-sans">
        <div className="mx-auto max-w-4xl rounded-2xl bg-white p-8 shadow-sm border border-slate-100">
          <div className="flex items-center justify-between border-b pb-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white">
                <Calendar className="h-6 w-6" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-slate-900">RoomSync Dashboard</h1>
                <p className="text-xs text-slate-500">Hệ thống Quản lý & Đặt phòng họp</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200 transition"
            >
              <LogOut className="h-4 w-4" /> Đăng xuất
            </button>
          </div>

          <div className="mt-8 space-y-6">
            <div className="flex items-center gap-3 rounded-xl bg-emerald-50 p-4 text-emerald-800 border border-emerald-100">
              <CheckCircle className="h-5 w-5 text-emerald-600 shrink-0" />
              <div>
                <p className="font-semibold text-sm">Đăng nhập thành công!</p>
                <p className="text-xs opacity-90">Bạn đang đăng nhập dưới quyền: <span className="font-bold uppercase">{userRole}</span></p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Phòng họp khả dụng</p>
                <p className="mt-2 text-3xl font-extrabold text-slate-900">8 / 12</p>
              </div>
              <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Lịch đặt hôm nay</p>
                <p className="mt-2 text-3xl font-extrabold text-blue-600">5 cuộc họp</p>
              </div>
              <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Trạng thái CSDL</p>
                <p className="mt-2 text-sm font-bold text-emerald-600">MySQL Connected</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Màn hình Đăng nhập (Mẫu chuẩn Figma RoomSync)
  return (
    <div className="flex min-h-screen w-full bg-white font-sans text-slate-800">
      {/* Khối bên trái: Form Đăng nhập */}
      <div className="flex w-full flex-col justify-between p-8 md:w-1/2 lg:p-16">
        <div>
          {/* Logo */}
          <div className="flex items-center gap-3 text-blue-600">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white shadow-md">
              <Calendar className="h-6 w-6" />
            </div>
            <span className="text-xl font-bold tracking-tight text-slate-900">RoomSync</span>
          </div>

          {/* Tiêu đề */}
          <div className="mt-12">
            <h1 className="text-3xl font-extrabold text-slate-900">Đăng nhập vào tài khoản</h1>
            <p className="mt-2 text-sm text-slate-500">Chào mừng trở lại. Nhập thông tin đăng nhập để tiếp tục.</p>
          </div>

          {/* Thông báo lỗi nếu sai thông tin */}
          {errorMessage && (
            <div className="mt-6 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-600 border border-red-100">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleLogin} className="mt-8 space-y-5">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                Tên đăng nhập / Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                <input
                  type="text"
                  required
                  placeholder="admin hoặc user1"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-slate-50/50 py-3 pl-11 pr-4 text-sm outline-none transition focus:border-blue-600 focus:bg-white focus:ring-2 focus:ring-blue-100"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                Mật khẩu
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-slate-50/50 py-3 pl-11 pr-11 text-sm outline-none transition focus:border-blue-600 focus:bg-white focus:ring-2 focus:ring-blue-100"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500" />
                <span className="text-slate-600">Ghi nhớ đăng nhập</span>
              </label>
              <a href="#" className="font-semibold text-blue-600 hover:underline">Quên mật khẩu?</a>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full rounded-lg bg-blue-600 py-3.5 text-sm font-semibold text-white shadow-md hover:bg-blue-700 active:scale-[0.99] transition disabled:opacity-50"
            >
              {isLoading ? 'Đang xác thực...' : 'Đăng Nhập'}
            </button>
          </form>

          {/* Gợi ý tài khoản thử nghiệm */}
          <div className="mt-8 rounded-lg bg-slate-50 p-3 text-center text-xs text-slate-500 border border-slate-100">
            <span className="font-semibold text-slate-700">Tài khoản thử nghiệm:</span><br />
            Admin: <code className="bg-slate-200 px-1 py-0.5 rounded text-slate-800">admin</code> / <code className="bg-slate-200 px-1 py-0.5 rounded text-slate-800">Admin@123</code><br />
            User: <code className="bg-slate-200 px-1 py-0.5 rounded text-slate-800">user1</code> / <code className="bg-slate-200 px-1 py-0.5 rounded text-slate-800">User@123</code>
          </div>
        </div>
      </div>

      {/* Khối bên phải: Banner xanh đậm */}
      <div className="hidden w-1/2 bg-slate-900 lg:flex flex-col justify-between p-12 text-white relative overflow-hidden">
        <div 
          className="absolute inset-0 bg-cover bg-center opacity-20 pointer-events-none"
          style={{ backgroundImage: `url('https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&q=80')` }}
        ></div>

        <div className="relative z-10 flex flex-wrap gap-2">
          {['Đặt phòng họp', 'Đồng bộ lịch', 'Phân tích dữ liệu', 'Hỗ trợ SSO'].map((tag, i) => (
            <span key={i} className="rounded-full bg-white/10 backdrop-blur-md px-4 py-1.5 text-xs font-medium text-slate-200 border border-white/10">
              {tag}
            </span>
          ))}
        </div>

        <div className="relative z-10 my-auto py-12">
          <h2 className="text-4xl font-extrabold leading-tight tracking-tight">
            Đặt đúng phòng họp,<br />mọi lúc bạn cần.
          </h2>
          <p className="mt-4 text-sm text-slate-300 max-w-md leading-relaxed">
            RoomSync giúp đội nhóm của bạn nắm rõ tình trạng toàn bộ phòng họp — đặt lịch, quản lý và tối ưu hoá tại một nơi duy nhất.
          </p>
        </div>

        <div className="relative z-10 grid grid-cols-3 gap-6 pt-8 border-t border-white/10">
          <div>
            <p className="text-2xl font-extrabold">2.400+</p>
            <p className="text-xs text-slate-400 mt-1">Phòng được quản lý</p>
          </div>
          <div>
            <p className="text-2xl font-extrabold">98,5%</p>
            <p className="text-xs text-slate-400 mt-1">Độ chính xác đặt phòng</p>
          </div>
          <div>
            <p className="text-2xl font-extrabold">340+</p>
            <p className="text-xs text-slate-400 mt-1">Khách hàng doanh nghiệp</p>
          </div>
        </div>
      </div>
    </div>
  );
}