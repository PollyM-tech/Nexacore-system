/* eslint-disable react-refresh/only-export-components */

import {
  createContext,
  useContext,
  useEffect,
  useState,
} from "react";

import {
  getMe,
  login as loginRequest,
} from "../api/auth";


const AuthContext = createContext(null);


export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  const [loading, setLoading] = useState(
    () => Boolean(localStorage.getItem("access_token"))
  );


  useEffect(() => {
    const token = localStorage.getItem("access_token");

    // There is no existing session to restore.
    if (!token) {
      return;
    }


    let cancelled = false;


    async function restoreSession() {
      try {
        const result = await getMe();

        if (cancelled) {
          return;
        }

        const currentUser = result.data.user;

        setUser(currentUser);

        localStorage.setItem(
          "user",
          JSON.stringify(currentUser)
        );

      } catch (error) {
        if (cancelled) {
          return;
        }

        console.error(
          "Unable to restore authentication:",
          error
        );

        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user");

        setUser(null);

      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }


    restoreSession();


    return () => {
      cancelled = true;
    };
  }, []);


  async function login(email, password) {
    const result = await loginRequest(
      email,
      password
    );

    const {
      access_token,
      refresh_token,
      user,
    } = result.data;


    localStorage.setItem(
      "access_token" ,
      access_token
    );

    localStorage.setItem(
      "refresh_token",
      refresh_token
    );

    localStorage.setItem(
      "user",
      JSON.stringify(user)
    );


    setUser(user);

    return user;
  }


  function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");

    setUser(null);
  }


  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}


export function useAuth(){
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth must be used inside AuthProvider"
    );
  }

  return context;
}