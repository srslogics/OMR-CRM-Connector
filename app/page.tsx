import { getSession } from './auth';
import Workspace from './workspace';
import Login from './login';
export const dynamic='force-dynamic';
export default async function Page(){try{const user=await getSession();return user?<Workspace signedIn email={user.phone}/>:<Login/>}catch{return <main><h1>Temporarily unavailable</h1><p>Please reload in a moment.</p></main>}}
